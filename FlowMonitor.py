import os
import subprocess
import time
from collections import deque
import threading
import math

from ApplicationSwitch_2 import *
from SwitchProperties import *


class FlowMonitor:               

        def __init__(self, samples=10, period=3, intervalTime=1.0, upperLimit=10*0.8, lowerLimit=10*0.6):
	
		self.nSamples=samples
		self.period=period
		self.intervalTime=intervalTime
		self.switchProperties=SwitchProperties()
		self.interfacesList = self.switchProperties.getInterfaces()
		self.completeInterfaceList=[]		

		for i in range(len(self.interfacesList)):
			completeInterfaceDict = dict.fromkeys(['name','dpid','capacity', 'lowerLimit', 'upperLimit', 'threshold', 'samples','useAverages','monitoring','isCongested','queueList'])
			completeInterfaceDict['name'] = self.interfacesList[i]['name']
			completeInterfaceDict['dpid'] = self.interfacesList[i]['dpid']
			completeInterfaceDict['capacity'] = self.interfacesList[i]['capacity']
			completeInterfaceDict['lowerLimit'] = lowerLimit
			completeInterfaceDict['upperLimit'] = upperLimit
			completeInterfaceDict['threshold'] = upperLimit
			completeInterfaceDict['samples'] = []
			completeInterfaceDict['prevEma'] = 0
			completeInterfaceDict['currentEma'] = 0
			completeInterfaceDict['useAverages'] = 0
			completeInterfaceDict['monitoring'] = 0
			completeInterfaceDict['isCongested'] = 0
			completeInterfaceDict['queueList'] = []					
			self.completeInterfaceList.append(completeInterfaceDict)

			for i in range(len(self.completeInterfaceList)):
				self.completeInterfaceList[i]['useAverages'] = deque( maxlen=self.nSamples )

			#Control variables
			self.threadsId=[]
			self.resetQueues()
			self.initWindow()			

        def resetQueues(self):

            for i in range(len(self.completeInterfaceList)):                
            	subprocess.check_output('ovs-ofctl del-flows ' + self.completeInterfaceList[i]['name'], shell=True)
                subprocess.check_output('./clear_queues.sh ' + self.completeInterfaceList[i]['name'], shell=True)

        def initWindow(self):

            for j in range(len(self.completeInterfaceList)):
                for i in range(self.nSamples):                
                    self.completeInterfaceList[j]['useAverages'].append(0)

            for i in range(self.nSamples):

                #sample list of dicts, each dict has ['name']['sample']
                result = self.getSample() # < ---- GOTTA CHECK THIS                                        
                for j in range(len(self.completeInterfaceList)):                    
                    lastSamples = result[j]['sample']
                    self.completeInterfaceList[j]['useAverages'].popleft()                    
                    self.completeInterfaceList[j]['useAverages'].append(lastSamples)                    

                if i == 0:
                    self.completeInterfaceList[j]['prevema'] = lastSamples                    

            for j in range(len(self.completeInterfaceList)):       
                for bar, close in enumerate(self.completeInterfaceList[j]['useAverages']):
                    self.completeInterfaceList[j]['currentEma'] = self.ema(bar, self.completeInterfaceList[j]['useAverages'], self.period, self.completeInterfaceList[j]['prevEma'], smoothing=None)
                    self.completeInterfaceList[j]['prevEma'] = self.completeInterfaceList[j]['currentEma']


	def updateWindow(self):

		for i in range(self.nSamples):

			# Sample list of dicts, each dict has ['name']['sample']
			result = self.getSample() # < ---- GOTTA CHECK THIS
			lastSamples=0

			for j in range(len(self.completeInterfaceList)):
				lastSamples = result[j]['sample']
				self.completeInterfaceList[j]['useAverages'].popleft()
				self.completeInterfaceList[j]['useAverages'].append(lastSamples)

			if i == 0:
				self.completeInterfaceList[j]['prevema'] = lastSamples
					
			for j in range(len(self.completeInterfaceList)):
				for bar, close in enumerate(self.completeInterfaceList[j]['useAverages']):
					self.completeInterfaceList[j]['currentEma'] = self.ema(bar, self.completeInterfaceList[j]['useAverages'], self.period, self.completeInterfaceList[j]['prevEma'], smoothing=None)
					self.completeInterfaceList[j]['prevEma'] = self.completeInterfaceList[j]['currentEma']				
		
        def startMonitoring(self):

		self.reportObject = ApplicationSwitch_2()
		self.monitoring=1	

		self.threadsId.append(threading.Thread(name = 'Monitor', target=self.monitor))
		self.threadsId[0].start()

	def stopMonitoring(self):
		self.monitoring=0

	#toDo: Handle
	def congestionStopped(self):
		self.isCongested=0

	def monitor(self):

		while self.monitoring == 1:

			try:
				self.updateWindow()
							
				for j in range(len(self.completeInterfaceList)):
					
					print "update, ema: " + str(self.completeInterfaceList[j]['currentEma'])
					print "current threshold: " + str(self.completeInterfaceList[j]['threshold'])
					if (self.completeInterfaceList[j]['isCongested'] == 0) and (self.completeInterfaceList[j]['currentEma'] >= self.completeInterfaceList[j]['threshold']):
						print "Congested"
						self.completeInterfaceList[j]['threshold']=self.completeInterfaceList[j]['lowerLimit']			
						print "Reporting congestion"							
						self.reportObject.congestionDetected(self.completeInterfaceList[j])						

					elif (self.completeInterfaceList[j]['isCongested'] == 1) and (self.completeInterfaceList[j]['currentEma'] <= self.completeInterfaceList[j]['threshold']):										
						self.completeInterfaceList[j]['isCongested']=0						
						self.completeInterfaceList[j]['threshold']=self.completeInterfaceList[j]['upperLimit']
						print "Congestion ceased"
						self.reportObject.congestionCeased(self.completeInterfaceList[j]['dpid'])

			except KeyboardInterrupt:
				print " \n *** So long and thanks for all the fish! *** "
				self.monitoring = 0
				break

	def createQueues(self, controllerMessage):

		for i in range(len(self.completeInterfaceList)):
			self.completeInterfaceList[i]['queueList']=self.initQueues(self.completeInterfaceList[i]['name'],controllerMessage['bwList'])
			self.setQueuesBw(self.completeInterfaceList[i]['queueList'], controllerMessage['bwList'])		
			self.reportObject.queuesReady(self.completeInterfaceList[i],controllerMessage['bwList'],self.completeInterfaceList[i]['queueList'])
			break

	def initQueues(self, interfaceName, bwList):
		
		print "Initing queues for: " + str(interfaceName)
		queuesList=[]
		qosString='ovs-vsctl -- set Port ' + interfaceName + ' qos=@fenceqos -- --id=@fenceqos create QoS type=linux-htb'
		queuesString=''

		for j in range(len(bwList)):
			aQueueDict=dict.fromkeys(['queueId','queueuuid','nw_src','nw_dst','bw'])
			aQueueDict['queueId']=j+1
			aQueueDict['nw_src']=bwList[j]['nw_src']
			aQueueDict['nw_dst']=bwList[j]['nw_dst']
			aQueueDict['bw'] = bwList[j]['bw']
			aQueue= ',' + str(aQueueDict['queueId']) +'=@queue' + str(aQueueDict['queueId'])
			queuesString=queuesString+aQueue
			print "Created queue dict: " + str(aQueueDict)
			queuesList.append(aQueueDict)

		queuesString='queues=0=@queue0'+queuesString
		#toDo: Check the string creation

		queuesCreation='-- --id=@queue0 create Queue other-config:max-rate=1000000000 '
		#toDo: Check the numqueues handling

		for j in range(len(bwList)):
			aCreation='-- --id=@queue' + str(queuesList[j]['queueId']) + ' create Queue other-config:max-rate=1000000000 '
			queuesCreation=queuesCreation+aCreation

		command=qosString + ' ' + queuesString + ' ' + queuesCreation
		print "Queue command: \n " + str(command)
		subprocess.check_output(command, shell=True)

		print "Queues list " + str(queuesList) 

		# Getting uuid of each queue
		queuesString = subprocess.check_output("ovs-vsctl list Queue", shell=True)
		print "Queues Ready: " + str(queuesString)

		allQueuesString = subprocess.check_output("ovs-vsctl list QoS  | grep queues", shell=True)
	
		for j in range(len(queuesList)):
			#uuid[i] = queuesString.split(":")[1].split(",")[i].split("=")[1]
			queuesList[j]['queueuuid']=allQueuesString.split(":")[1].split(",")[j+1].split("=")[1].split('}\n')[0].strip()

		print "Queue List: " + str(queuesList)
		return queuesList

	def setQueuesBw(self, queuesList, flowBwList):

		for i in range(len(queuesList)): 
			subprocess.check_output("ovs-vsctl set queue " + queuesList[i]['queueuuid'] + " other-config:max-rate="+str(queuesList[i]['bw']), shell=True)			

	def getUuid(self):
		uuid=subprocess.check_output("ovs-vsctl list qos | grep queues | awk '{print $4;}'", shell=True).split('=')[1].split('}')[0]
		return uuid

        def getRate(self,uuid):
		rate=float(subprocess.check_output("ovs-vsctl list queue " + uuid + " | grep other_config | awk '{print $3;}'", shell=True).split('=')[1].split('"')[1])
		return rate
	

        def ema(self, bar, series, period, prevma, smoothing=None):
            '''Returns the Exponential Moving Average of a series.
             
            Keyword arguments:
            bar         -- currrent index or location of the series
            series      -- series of values to be averaged
            period      -- number of values in the series to average
            prevma      -- previous exponential moving average
            smoothing   -- smoothing factor to use in the series.
                valid values: between 0 & 1.
                default: None - which then uses formula = 2.0 / (period + 1.0)
                closer to 1 to gives greater weight to recent values - less smooth
                closer to 0 gives greater weight to older values -- more smooth
            '''

            smoothing = 0.8

            if bar <= 0:
                return series[0]
             
            elif bar < period:
                return self.cumulative_sma(bar, series, prevma)
             
            return prevma + smoothing * (series[bar] - prevma)

        def cumulative_sma(self, bar, series, prevma):
            """
            Returns the cumulative or unweighted simple moving average.
            Avoids averaging the entire series on each call.
             
            Keyword arguments:
            bar     --  current index or location of the value in the series
            series  --  list or tuple of data to average
            prevma  --  previous average (n - 1) of the series.
            """
             
            if bar <= 0:
                return series[0]
                 
            else:
                return prevma + ((series[bar] - prevma) / (bar + 1.0))

	def getSample(self, intervalTime=1.0):
		samplesList=[]

		for j in range(len(self.completeInterfaceList)):
			sampleDict=dict.fromkeys(['interfaceName'],['sample'])
			samplesList.append(sampleDict)

		#lists to Store first and second sample value of each interface
		# Each value of a and b represents a sample taken in each interface
		a=[]
		b=[]

		for j in range(len(self.completeInterfaceList)):
			a.append((float(subprocess.check_output("cat /proc/net/dev | grep " + self.completeInterfaceList[j]['name'] + " | awk '{print $10;}'", shell=True).split('\n')[0])))

		sleep(intervalTime)

		for j in range(len(self.completeInterfaceList)):

			b.append((float(subprocess.check_output("cat /proc/net/dev | grep " + self.completeInterfaceList[j]['name'] + " | awk '{print $10;}'", shell=True).split('\n')[0])))
			samplesList[j]['name'] = self.completeInterfaceList[j]['name']
			#samplesList[j]['sample']=((b[j]-a[j])/1048576) In MBytes
			samplesList[j]['sample']=b[j]-a[j]
		return samplesList

if __name__=="__main__":

    nSamples=10
    period = 3  #number of bars to average
    intervalTime=1.0

    #toDo: Handle this as a percentage of total link capacity
    upperLimit = 0.4
    lowerLimit = 0.41

    useAverages = deque( maxlen=nSamples )
    code = FlowMonitor(nSamples, intervalTime, upperLimit)
    code.startMonitoring()
