import os
import subprocess
import time
from collections import deque
import threading

from ApplicationSwitch import *
from SwitchProperties import *


class FlowMonitor:


        def resetQueues(self):

            for i in range(len(self.completeInterfaceList)):                
                subprocess.check_output('./clear_queues.sh ' + self.completeInterfaceList[i]['name'], shell=True)
                subprocess.check_output('ovs-ofctl del-flows ' + self.completeInterfaceList[i]['name'], shell=True)

        def __init__(self, samples=10, period=3, intervalTime=1.0, upperLimit=10*0.8, lowerLimit=10*0.6):

		# SOME DATA LIKE INTERFACES NAME AND ETC, SHOULD BE OBTAINED USING SWITCH CHARACTERISTICS!!
		self.nSamples=samples
		self.period=period
		self.intervalTime=intervalTime
		self.switchProperties=SwitchProperties()
		self.interfacesList = self.switchProperties.getInterfaces()
		self.completeInterfaceList=[]

		for i in range(len(self.interfacesList)):
			completeInterfaceDict = dict.fromkeys(['name','dpid','capacity', 'lowerLimit', 'upperLimit', 'threshold', 'samples','useAverages','monitoring','isCongested','numQueues'])
			completeInterfaceDict['name'] = code.interfacesList[i]['name']
			completeInterfaceDict['dpid'] = code.interfacesList[i]['dpid']
			completeInterfaceDict['capacity'] = code.interfacesList[i]['capacity']
			completeInterfaceDict['lowerLimit'] = lowerLimit
			completeInterfaceDict['upperLimit'] = upperLimit
			completeInterfaceDict['threshold'] = threshold
			completeInterfaceDict['samples'] = []
			completeInterfaceDict['prevEma'] = 0
			completeInterfaceDict['currentEma'] = 0
			completeInterfaceDict['useAverages'] = 0
			completeInterfaceDict['monitoring'] = 0
			completeInterfaceDict['isCongested'] = 0
			completeInterfaceDict['numQueues'] = 10
			self.completeInterfaceList.append(completeInterfaceDict)
    

            #In Mbps: Threshold is link capacity * some factor
            # toDo: It should receive a % of occupation and it should measure the link capacity.
            #self.upperLimit = upperLimit
            #self.lowerLimit = lowerLimit
            #self.threshold  = self.upperLimit

            #self.useAverages = deque( maxlen=self.nSamples )
            for i in range(len(self.completeInterfaceList)):
                self.completeInterfaceList[i]['useAverages'] = deque( maxlen=self.nSamples )

            #Control variables
            self.threadId=0
	            
	    #self.interface='eth0'
	    
        # toDo: Obtain this data from the module that handles de switch information

            self.resetQueues()
            self.initWindow()

            print 'Initialization proccess finished, average: ' + str(self.useAverages)

        def initWindow(self):

            for j in range(len(self.completeInterfaceList)):
                for i in range(self.nSamples):                
                    self.completeInterfaceList[j]['useAverages'].append(0)
            print self.useAverages

            for i in range(self.nSamples):

                #sample list of dicts, each dict has ['name']['sample']
                result = self.getSample() # < ---- GOTTA CHECK THIS                                        
                for j in range(len(self.completeInterfaceList)):                    
                    lastSamples = result[j]['sample']
                    self.completeInterfaceList[j]['useAverages'].popleft()                    
                    self.completeInterfaceList[j]['useAverages'].append(lastSamples)                    

                #print useAverages

                if i == 0:
                    self.completeInterfaceList[j]['prevema'] = self.lastSamples
                    #self.prevema = self.lastSamples

            for j in range(len(self.completeInterfaceList)):       
                for bar, close in enumerate(self.completeInterfaceList[j]['useAverages']):
                    self.completeInterfaceList[j]['currentEma'] = self.ema(bar, self.completeInterfaceList[j]['useAverages'], self.period, self.completeInterfaceList[j]['prevEma'], smoothing=None)
                    self.completeInterfaceList[j]['prevEma'] = self.completeInterfaceList[j]['currentEma']

	def updateWindow(self):

		for i in range(self.nSamples):

			#sample list of dicts, each dict has ['name']['sample']
			result = self.getSample() # < ---- GOTTA CHECK THIS

			for j in range(len(self.completeInterfaceList)):
				lastSamples = result[j]['sample']
				self.completeInterfaceList[j]['useAverages'].popleft()
				self.completeInterfaceList[j]['useAverages'].append(lastSamples)

			if i == 0:
				self.completeInterfaceList[j]['prevema'] = self.lastSamples
	
			for j in range(len(self.completeInterfaceList)):
				for bar, close in enumerate(self.completeInterfaceList[j]['useAverages']):
					self.completeInterfaceList[j]['currentEma'] = self.ema(bar, self.completeInterfaceList[j]['useAverages'], self.period, self.completeInterfaceList[j]['prevEma'], smoothing=None)
					self.completeInterfaceList[j]['prevEma'] = self.completeInterfaceList[j]['currentEma']
				print "Current channel occupation for interface " + str(self.completeInterfaceList[j]['name']) + " : " + str(self.completeInterfaceList[j]['currentEma'])
		
        def startMonitoring(self):
            
            print self.completeInterfaceList
            self.reportObject = ApplicationSwitch()

            self.monitoring=1            
            self.threadId = threading.Thread(name = 'Monitor', target=self.monitor)
            self.threadId.start()    

        def stopMonitoring(self):
            self.monitoring=0                  

        #toDo: Handle
        def congestionStopped(self):
            self.isCongested=0

	def monitor(self):

		while self.monitoring == 1:
			try:
				self.updateWindow()
				#Has histeresis
				for j in range(len(self.completeInterfaceList)):
					if (self.completeInterfaceList[j]['isCongested'] == 0) and (self.completeInterfaceList[j]['currentEma'] >= self.completeInterfaceList[j]['threshold']):
						print 'Congestion detected in interface: ' + self.completeInterfaceList[j]['name']
						self.completeInterfaceList[j]['isCongested']=1
						self.completeInterfaceList[j]['threshold']=self.completeInterfaceList[j]['lowerLimit']
						self.initQueues()
						self.reportObject.congestionDetected(self.completeInterfaceList[j]['dpid'])
						#toDo: After of reporting, it should init the queues and wait for further actions from the controller
						print 'Decrementing..'

					elif (self.completeInterfaceList[j]['isCongested'] == 1) and (self.completeInterfaceList[j]['currentEma'] <= self.completeInterfaceList[j]['threshold']):
						print 'Congestion ceased'
						self.completeInterfaceList[j]['isCongested']=0
						self.completeInterfaceList[j]['threshold']=self.completeInterfaceList[j]['upperLimit']
						self.reportObject.congestionDetected(self.completeInterfaceList[j]['dpid'])

					if (self.completeInterfaceList[j]['isCongested'] == 1) and (self.completeInterfaceList[j]['currentEma'] >= self.completeInterfaceList[j]['lowerLimit']):
						#Decrement delta
						print 'Decrementing..'

			except KeyboardInterrupt:
				print " \n *** So long and thanks for all the fish! *** "
				self.monitoring = 0
				break

	def initQueues(self):

        #toDo: Handle for each interface
		subprocess.check_output('./clear_queues.sh ' + self.interface + ' ' + self.interface + 'br', shell=True)
		self.queues_uuid=[]

		qosString='ovs-vsctl -- set Port ' + self.interface + ' qos=@testqos -- --id=@testqos create QoS type=linux-htb'
		queuesString=''

		for i in range(self.numQueues):
		        aQueue= ',' + str(i+1) +'=@queue' + str(i+1)
		        queuesString=queuesString+aQueue
		
		queuesString='queues=0=@queue0'+queuesString

        #toDo: Check the string creation
		queuesCreation='-- --id=@queue0 create Queue other-config:max-rate=1000000000 '

        #toDo: Check the numqueues handling
		for i in range(self.numQueues):

		        aCreation='-- --id=@queue' + str(i+1) + ' create Queue other-config:max-rate=1000000000 '
		        queuesCreation=queuesCreation+aCreation

		command=qosString + ' ' + queuesString + ' ' + queuesCreation	
		subprocess.check_output(command, shell=True)

		for i in range(self.numQueues+1):

		        j=i+3
		        awk="{print $" + str(j) + ";}'"
		        awkString="awk '" + awk
		        auxString=subprocess.check_output('ovs-vsctl list qos | grep queues | ' + awkString, shell=True).split('=')[1]
		        self.queues_uuid.append({'id':i,'uuid':auxString[:len(auxString)-2]})

		print self.queues_uuid
		#subprocess.check_output('ovs-ofctl add-flow ' + self.interface + 'br in_port=LOCAL,priority=0,actions=enqueue:1:0', shell=True)		

	def getUuid(self):
		uuid=subprocess.check_output("ovs-vsctl list qos | grep queues | awk '{print $4;}'", shell=True).split('=')[1].split('}')[0]
		return uuid

        def getRate(self,uuid):
		#uuid=subprocess.check_output("ovs-vsctl list qos | grep queues | awk '{print $4;}'", shell=True).split('=')[1].split('}')[0]
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

        #toDo: Handle to manage all interfaces samples
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
			samplesList[j]['sample']=((b[j]-a[j])/1048576)

		return samplesList

    #todo: Improve the flow dictionary
	def createFlowDict(self, nwDst, interface):		

		total=subprocess.check_output("ovs-ofctl dump-flows " + interface +"br", shell=True)

		if len(total) != 27:

                #todo: This line is broken!!
		        flows=subprocess.check_output("ovs-ofctl dump-flows " + interface + "br | grep nw_dst=" + nwDst, shell=True).split('\n')

		        for i in range(len(flows)):

		                items=flows[i].split(',')
		                pairs=[]

		                for i in range(len(items)):
		                        pairs.append(items[i].split('='))

                		twoPairs=[]

		                for i in range(len(pairs)):
		                        if len(pairs[i]) == 2:
		                                twoPairs.append(pairs[i])

		                flowsDict.append(dict((k.strip(), v.strip()) for k,v in twoPairs))

	        #Improve! :P
	        flowsDict=flowsDict[0:len(flowsDict)-1]


#todo: Main is broken, fix it, is it still broken?
if __name__=="__main__":

    nSamples=10
    period = 3  #number of bars to average
    intervalTime=1.0

    #toDo: Handle this as a percentage of total link capacity
    upperLimit = 8.4
    lowerLimit = 0.6

    useAverages = deque( maxlen=nSamples )
    code = FlowMonitor(nSamples, intervalTime, upperLimit)
    code.startMonitoring()
