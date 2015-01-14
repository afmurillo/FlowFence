import os
import subprocess
import time
from collections import deque
import threading
import math

from ApplicationSwitch import *
from SwitchProperties import *


class FlowMonitor:

        def resetQueues(self):

            for i in range(len(self.completeInterfaceList)):                
            	subprocess.check_output('ovs-ofctl del-flows ' + self.completeInterfaceList[i]['name'], shell=True)
                subprocess.check_output('./clear_queues.sh ' + self.completeInterfaceList[i]['name'], shell=True)
                
        def __init__(self, samples=10, period=3, intervalTime=1.0, upperLimit=10*0.8, lowerLimit=10*0.6):

		# SOME DATA LIKE INTERFACES NAME AND ETC, SHOULD BE OBTAINED USING SWITCH CHARACTERISTICS!!
		self.nSamples=samples
		self.period=period
		self.intervalTime=intervalTime
		self.switchProperties=SwitchProperties()
		self.interfacesList = self.switchProperties.getInterfaces()
		self.completeInterfaceList=[]
		self.completeFlowList=[]
		self.k=1.0 #When k=0.4, actually, k is 0.6 in "CPU" time
		self.measuredK=0.2

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
	
			flowIntDict = dict.fromkeys(['interfaceName'],['flowList'])
			flowIntDict['interfaceName']= self.interfacesList[i]['name']
			flowIntDict['flowList']=[]					
			self.completeFlowList.append(flowIntDict)

			for i in range(len(self.completeInterfaceList)):
				self.completeInterfaceList[i]['useAverages'] = deque( maxlen=self.nSamples )

			#Control variables
			self.threadsId=[]
			self.resetQueues()
			self.initWindow()			

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
                    #self.prevema = self.lastSamples

            for j in range(len(self.completeInterfaceList)):       
                for bar, close in enumerate(self.completeInterfaceList[j]['useAverages']):
                    self.completeInterfaceList[j]['currentEma'] = self.ema(bar, self.completeInterfaceList[j]['useAverages'], self.period, self.completeInterfaceList[j]['prevEma'], smoothing=None)
                    self.completeInterfaceList[j]['prevEma'] = self.completeInterfaceList[j]['currentEma']

	def updateFlows(self):

		while self.monitoring == 1:
			try:			
				# We get samples from all the flows in all interfaces								
				self.getFlows()
			except KeyboardInterrupt:
				self.monitoring=0
				break

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

		self.reportObject = ApplicationSwitch()
		self.monitoring=1
		
		self.threadsId.append(threading.Thread(name = 'updateFlows', target=self.updateFlows))
		self.threadsId[0].start()

		self.threadsId.append(threading.Thread(name = 'Monitor', target=self.monitor))
		self.threadsId[1].start()

	def stopMonitoring(self):
		self.monitoring=0

	#toDo: Handle
	def congestionStopped(self):
		self.isCongested=0

	def monitor(self):

		while self.monitoring == 1:
			try:
				self.updateWindow()
				
				print "Complete Interface List: " + str(self.completeInterfaceList)				
				for j in range(len(self.completeInterfaceList)):
					
					print "Actual FlowList: " + str(self.completeFlowList[j]['flowList'])
					self.completeInterfaceList[j]['queueList']=self.initQueues(self.completeInterfaceList[j]['name'],self.completeFlowList[j]['flowList'])
					print "Created queues: " + str(self.completeInterfaceList[j]['queueList'])
					#print "Interface statistics: " + str(self.completeInterfaceList[j]['currentEma']) + " Threshold: " + str(self.completeInterfaceList[j]['threshold'])
					if (self.completeInterfaceList[j]['isCongested'] == 0) and (self.completeInterfaceList[j]['currentEma'] >= self.completeInterfaceList[j]['threshold']):
						self.completeInterfaceList[j]['isCongested']=1
						self.completeInterfaceList[j]['threshold']=self.completeInterfaceList[j]['lowerLimit']
						#self.calculateControls(j)
						if len(self.completeFlowList[j]['flowList']) > 0:
							self.reportObject.congestionDetected(self.completeInterfaceList[j], self.completeFlowList[j]['flowList'])
						#toDo: After of reporting, it should init the queues and wait for further actions from the controller

					elif (self.completeInterfaceList[j]['isCongested'] == 1) and (self.completeInterfaceList[j]['currentEma'] <= self.completeInterfaceList[j]['threshold']):
						self.completeInterfaceList[j]['isCongested']=0
						self.completeInterfaceList[j]['threshold']=self.completeInterfaceList[j]['upperLimit']
						self.reportObject.congestionDetected(self.completeInterfaceList[j]['dpid'], self.completeFlowList[j]['flowList'])

					if (self.completeInterfaceList[j]['isCongested'] == 1) and (self.completeInterfaceList[j]['currentEma'] >= self.completeInterfaceList[j]['lowerLimit']):
						#toDo: Check if this case is still neccessary
						#Decrement delta
						print 'Decrementing..'

			except KeyboardInterrupt:
				print " \n *** So long and thanks for all the fish! *** "
				self.monitoring = 0
				break

	def initQueues(self, interfaceName, flowList):
		
		print "Initing queues for: " + str(interfaceName)
		queuesList=[]
		qosString='ovs-vsctl -- set Port ' + interfaceName + ' qos=@fenceqos -- --id=@fenceqos create QoS type=linux-htb'
		queuesString=''

		for j in range(len(flowList)):
			aQueueDict=dict.fromkeys(['queueId','queueuuid','nw_src','nw_dst','bw'])
			aQueueDict['queueId']=j+1
			aQueueDict['nw_src']=flowList[j]['nw_src']
			aQueueDict['nw_dst']=flowList[j]['nw_dst']
			aQueue= ',' + str(aQueueDict['queueId']) +'=@queue' + str(aQueueDict['queueId'])
			queuesString=queuesString+aQueue
			print "Created queue dict: " + str(aQueueDict)
			queuesList.append(aQueueDict)

		queuesString='queues=0=@queue0'+queuesString
		#toDo: Check the string creation

		queuesCreation='-- --id=@queue0 create Queue other-config:max-rate=1000000000 '
		#toDo: Check the numqueues handling

		print "Queue List: " + str(queuesList)

		for j in range(len(flowList)):
			aCreation='-- --id=@queue' + str(queuesList[j]['queueId']) + ' create Queue other-config:max-rate=1000000000 '
			queuesCreation=queuesCreation+aCreation

		command=qosString + ' ' + queuesString + ' ' + queuesCreation
		print "Queue command: \n " + str(command)
		subprocess.check_output(command, shell=True)

		for j in range(len(flowList)):
			k=j+3
			awk="{print $" + str(k) + ";}'"
			awkString="awk '" + awk
			auxString=subprocess.check_output('ovs-vsctl list qos | grep queues | ' + awkString, shell=True).split('=')[1]
			queuesList[j]['queueuuid']={'id':j,'uuid':auxString[:len(auxString)-2]}
			#self.queues_uuid.append({'id':i,'uuid':auxString[:len(auxString)-2]})

			#subprocess.check_output('ovs-ofctl add-flow ' + self.interface + 'br in_port=LOCAL,priority=0,actions=enqueue:1:0', shell=True)		
		return queuesList

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

	def calculateControls(self, anInterfaceIndex):
		self.classifyFlows(anInterfaceIndex)
		

	def classifyFlows(self, anInterfaceIndex):
		for i in range(len(self.completeFlowList[anInterfaceIndex]['flowList'])):
			if self.completeFlowList[anInterfaceIndex]['flowList'][i]['arrivalRate'] > (self.completeInterfaceList[anInterfaceIndex]['capacity']/len(self.completeFlowList[anInterfaceIndex]['flowList'])):
				self.completeFlowList[anInterfaceIndex]['flowList'][i]['goodBehaved']=0

	def getFlows(self):
		# A list of dicts is created for each interface
		# Dict estructure: dl_src, dl_dst, nw_src, nw_dst, length(bytes), action			

		# We get samples from all the flows in all interfaces
		time1=time()
		#interfacesFlowString=dict.fromkeys(['interfaceName','string'])
		interfacesFlowPrevStringList=[]
		interfacesFlowStringList=[]		

		for i in range(len(self.completeInterfaceList)):			
			interfacesFlowString=dict.fromkeys(['interfaceName','string'])
			interfacesFlowString['interfaceName'] =  self.completeInterfaceList[i]['name']
			interfacesFlowString['string']=subprocess.check_output('./flows.sh ' + self.completeInterfaceList[i]['name'], shell=True)			
			interfacesFlowPrevStringList.append(interfacesFlowString)
			
		# toDo: Check a better way of doing this, what happens with flows that die?		
		sleep(self.k)
		self.measuredK = time() - time1

		for i in range(len(self.completeInterfaceList)):

			interfacesFlowString=dict.fromkeys(['interfaceName','string'])
			interfacesFlowString['interfaceName'] =  self.completeInterfaceList[i]['name']

			interfacesFlowString['string']=subprocess.check_output('./flows.sh ' + interfacesFlowString['interfaceName'], shell=True)
			interfacesFlowStringList.append(interfacesFlowString)


		for j in range(len(self.completeInterfaceList)):			
			
			prevNumFlows = int(interfacesFlowPrevStringList[j]['string'].split('\n')[0].split('=')[1])
			numFlows=int(interfacesFlowStringList[j]['string'].split('\n')[0].split('=')[1])
			#numFlows=int(flowString.split('\n')[0].split('=')[1])
			flowList=[]
					

			#this cycle runs over all the flows in the string
			for i in range(numFlows):

				flowDict=dict.fromkeys(['dl_src','dl_dst','nw_src','nw_dst','packets','length','arrivalRate', 'oldArrivalRate','action','goodBehaved'])
				flowDict['dl_src']=interfacesFlowStringList[j]['string'].split('\n')[1].split('=')[1].split(' ')[i]
				flowDict['dl_dst']=interfacesFlowStringList[j]['string'].split('\n')[2].split('=')[1].split(' ')[i]
				flowDict['nw_src']=interfacesFlowStringList[j]['string'].split('\n')[3].split('=')[1].split(' ')[i]
				flowDict['nw_dst']=interfacesFlowStringList[j]['string'].split('\n')[4].split('=')[1].split(' ')[i]
				flowDict['action']=interfacesFlowStringList[j]['string'].split('\n')[7].split('=')[1].split(' ')[i]

				aux1 = interfacesFlowStringList[j]['string'].split('\n')[5].split('=')[1].split(' ')[i]

				if (numFlows <= prevNumFlows):
					aux2 = interfacesFlowPrevStringList[j]['string'].split('\n')[5].split('=')[1].split(' ')[i]
				else:	
					aux2 = 0

				#check if this is still necessary
				if (aux1 is not None) and (aux2 is not None):
					flowDict['packets']=int(aux1) - int(aux2)
				else:
					flowDict['packets']=0
				
				aux1 = interfacesFlowStringList[j]['string'].split('\n')[6].split('=')[1].split(' ')[i]

				if (numFlows <= prevNumFlows):					
					aux2 = interfacesFlowPrevStringList[j]['string'].split('\n')[6].split('=')[1].split(' ')[i]
				else:	
					aux2 = 0

				if (aux1 is not None) and (aux2 is not None):
					flowDict['length']=int(aux1) - int(aux2)
				else:
					flowDict['length']=0

				# Here we should validate if the flow exists, if not, append; if yes overwrite values and update Ri
				flowIndex = self.checkIfFlowExists(j, flowDict)

				#Flow does not exist
				if flowIndex == -1:
					flowDict['oldArrivalRate'] = 0.0
					flowDict['goodBehaved'] = 0
					flowDict['arrivalRate'] = self.calculateArrivalRate(flowDict['packets'], flowDict['length'], self.measuredK, 0.0 )
					self.completeFlowList[j]['flowList'].append(flowDict)

				else:
					flowDict['oldArrivalRate'] = self.completeFlowList[j]['flowList'][flowIndex]['arrivalRate']
					#flowDict['oldArrivalRate'] = flowDict['arrivalRate']
					flowDict['arrivalRate'] = self.calculateArrivalRate(flowDict['packets'], flowDict['length'], self.measuredK, flowDict['oldArrivalRate'] )
					self.completeFlowList[j]['flowList'][flowIndex] = flowDict								
	
				# Finally we should check if according to our last sample, a flow in flowList stopped existing							
				for k in range(len(self.completeFlowList[j]['flowList'])):
					if (self.checkIfFlowStopped(interfacesFlowStringList[j]['string'], flowDict)):
						#splice
						#self.completeFlowList[j]['flowList'].remove(k)
						print "Should remove this flow"

				# Flowlist is empty, start filling it
				if not self.completeFlowList[j]['flowList']:
					flowDict['oldArrivalRate'] = 0.0
					flowDict['goodBehaved'] = 0
					flowDict['arrivalRate'] = self.calculateArrivalRate(flowDict['packets'], flowDict['length'], self.measuredK, 0.0 )
					self.completeFlowList[j]['flowList'].append(flowDict)

	def checkIfFlowStopped(self, aFlowString, aFlowDict):

		# If dL_src exists, checks in that flow if dl_dst and other fields coincide, if true: Flow exists				
		numFlows=int(aFlowString.split('\n')[0].split('=')[1])
		dl_srcExists = 0
		flowIndex = -1

		for i in range(numFlows):
			#now we are doing this ds_ip, we have to check if there's always a unique pair nw_dst and dl_src and dl_dst
			if aFlowDict['nw_dst'] == aFlowString.split('\n')[4].split('=')[1].split(' ')[i]:
																
				dl_srcExists = 1
				flowIndex = i
				break

		if dl_srcExists == 0:
			return True
		else:
			
			if (aFlowDict['dl_dst'] == aFlowString.split('\n')[2].split('=')[1].split(' ')[flowIndex]) and (aFlowDict['nw_src'] == aFlowString.split('\n')[3].split('=')[1].split(' ')[flowIndex]) and (aFlowDict['dl_src'] == aFlowString.split('\n')[1].split('=')[1].split(' ')[flowIndex]):
				return False
			else:
				return True

	def checkIfFlowExists(self, anInterfaceIndex, aFlowDict):
			#toDo: Comparation with "in values" does not work, we should make either a hash in correct order or a case case comparation
			for i in range(len(self.completeFlowList[anInterfaceIndex]['flowList'])):

				if (aFlowDict['dl_src'] == self.completeFlowList[anInterfaceIndex]['flowList'][i]['dl_src']) and (aFlowDict['dl_dst'] == self.completeFlowList[anInterfaceIndex]['flowList'][i]['dl_dst']) and (aFlowDict['nw_src'] == self.completeFlowList[anInterfaceIndex]['flowList'][i]['nw_src']) and (aFlowDict['nw_dst'] == self.completeFlowList[anInterfaceIndex]['flowList'][i]['nw_dst']):
					return i

			return -1			
			
	def calculateArrivalRate(self, packets, length, measuredK, oldArrivalRate):			

		if packets <= 0:
			return length/measuredK		

		if oldArrivalRate <= 0:
			return (1 - math.exp(-measuredK/self.k))*(length/measuredK)
		else:
			return (1 - math.exp(-measuredK/self.k))*(length/measuredK) + math.exp(-measuredK/(self.k*oldArrivalRate))

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
