import os
import subprocess
import time
from collections import deque
import threading

from ApplicationSwitch import *


class LinkMonitoring:

        def __init__(self, dpid, samples=10, period=3, intervalTime=1.0, upperLimit=10*0.8, lowerLimit=10*0.6, incr=500000, decr=0.5 ):

            self.nSamples=samples
            self.period=period
            
            self.intervalTime=intervalTime

            #In Mbps: Threshold is link capacity * some factor
            self.upperLimit = upperLimit
            self.lowerLimit = lowerLimit
	    self.threshold  = self.upperLimit

            self.useAverages = deque( maxlen=self.nSamples )

            #Control variables
            self.monitoring=0            
            self.threadId=0
            self.isCongested=0
            self.currentRate=0
            self.decr=decr
            self.incr=incr

	    #Queues variables
            self.numQueues=10
	    self.interface='eth0'
	    
	    self.dpid=dpid

	    subprocess.check_output('./clear_queues.sh ' + self.interface + ' ' + self.interface + 'br', shell=True)
   	    subprocess.check_output('ovs-ofctl del-flows ' + self.interface + 'br', shell=True)

            for i in range(10):
                self.useAverages.append(0)

            print self.useAverages


            for i in range(10):

                self.result = self.getSamples(1) # < ---- GOTTA CHECK THIS
                self.lastSamples = self.result[0]
                self.useAverages.popleft()
                self.useAverages.append(self.lastSamples)

                #print useAverages

                if i == 0:
                    self.prevema = self.lastSamples

            for bar, close in enumerate(self.useAverages):

                self.currentema = self.ema(bar, self.useAverages, self.period, self.prevema, smoothing=None)
                self.revema = self.currentema
                self.lastEma = 0
                
            print 'Initialization proccess finished, average: ' + str(self.useAverages)

        def startMonitoring(self):

            #toDo: Pretty Nasty, try to improve
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

                    result = self.getSamples(1) # < ---- GOTTA CHECK THIS
                    lastSamples = result[0]

		    self.useAverages.popleft()
		    self.useAverages.append(lastSamples)

                    for bar, close in enumerate(self.useAverages):

                        self.currentema = self.ema(bar, self.useAverages, self.period, self.prevema, smoothing=None)                        
                        self.prevema = self.currentema

		    #print 'Current ema'
                    #print self.currentema

		    #print 'Prev ema'
		    #print self.lastEma

		    #Has histeresis
                    if (self.isCongested == 0) and (self.currentema >= self.threshold):
                        print 'Congestion detected'                    
                        self.isCongested=1
			self.threshold=self.lowerLimit
			self.initQueues()
                        self.reportObject.congestionDetected(self.dpid)
                       
                        print 'Decrementing..'
                        newRate = 100000000/self.numQueues

                        for i in range(self.numQueues):
				subprocess.check_output("ovs-vsctl set queue " + self.queues_uuid[i+1]['uuid'] + " other-config:max-rate="+str(newRate), shell=True)
                        flows=subprocess.check_output("ovs-ofctl dump-flows eth0br", shell=True)
                        print flows
                 
                    elif (self.isCongested == 1) and (self.currentema <= self.threshold):

                        print 'Congestion ceased'
                        self.isCongested=0
			self.threshold=self.upperLimit                        

                        #subprocess.check_output('ovs-ofctl del-flows ' + self.interface + 'br', shell=True)
			#subprocess.check_output('./clear_queues.sh ' + self.interface + ' ' + self.interface + 'br', shell=True)
	                #self.queues_uuid=[]

                        self.reportObject.congestionCeased(self.dpid)

                    if (self.isCongested == 1) and (self.currentema >= self.lowerLimit):
                        
                        #Decrement delta
			print 'Decrementing..'
			newRate = 100000000/self.numQueues

			for i in range(self.numQueues): 
				subprocess.check_output("ovs-vsctl set queue " + self.queues_uuid[i+1]['uuid'] + " other-config:max-rate="+str(newRate), shell=True)
			flows=subprocess.check_output("ovs-ofctl dump-flows eth0br", shell=True)
			print flows

	def initQueues(self):

		subprocess.check_output('./clear_queues.sh ' + self.interface + ' ' + self.interface + 'br', shell=True)
		self.queues_uuid=[]

		qosString='ovs-vsctl -- set Port ' + self.interface + ' qos=@testqos -- --id=@testqos create QoS type=linux-htb'
		queuesString=''

		for i in range(self.numQueues):
		        aQueue= ',' + str(i+1) +'=@queue' + str(i+1)
		        queuesString=queuesString+aQueue
		
		queuesString='queues=0=@queue0'+queuesString
		queuesCreation='-- --id=@queue0 create Queue other-config:max-rate=1000000000 '

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

        def getSamples(self, nSamples=10, intervalTime=1.0):

            someSamples=[]

            for i in range(nSamples):

                #samples.append(int(subprocess.check_output("ifconfig eth0 | grep 'TX bytes' | awk '{print $6;}' | cut -d ':' -f2", shell=True).split('\n')[0]))
                a=(float(subprocess.check_output("cat /proc/net/dev | grep eth0br | awk '{print $10;}'", shell=True).split('\n')[0]))
                time.sleep(self.intervalTime)
                b=(float(subprocess.check_output("cat /proc/net/dev | grep eth0br | awk '{print $10;}'", shell=True).split('\n')[0]))

                someSamples.append((b-a)/1048576)
                
            return someSamples  

	def createFlowDict(self, nwDst, interface):		

		total=subprocess.check_output("ovs-ofctl dump-flows " + interface +"br", shell=True)

		if len(total) != 27:

		        flows=subprocess.check_output("ovs-ofctl dump-flows " + interface + "br | grep nw_dst=" + nwDst, shell=True).split('$

		        flowsDict=[]

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


#todo: Main is broken, fix it
if __name__=="__main__":

    code = LinkMonitoring()
    
    nSamples=10
    period = 3  #number of bars to average
    intervalTime=1.0

    #In Mbps: Threshold is link capacity * some factor
    upperLimit = 8.4

    useAverages = deque( maxlen=nSamples )

    # Initialization proccess

    for i in range(10):
        useAverages.append(0)

    print useAverages


    for i in range(10):

        result = code.getSamples(1) # < ---- GOTTA CHECK THIS
        lastSamples = result[0]
        useAverages.popleft()
        useAverages.append(lastSamples)

        #print useAverages

        if i == 0:
            prevema = lastSamples

    for bar, close in enumerate(useAverages):

        currentema = code.ema(bar, useAverages, period, prevema, smoothing=None)
        prevema = currentema
        

    print 'Initialization proccess finished, average: ' + str(useAverages)

    while True:

        try:

            result = code.getSamples(1) # < ---- GOTTA CHECK THIS
            lastSamples = result[0]

            if i == 0:

                prevema = lastSamples

            for bar, close in enumerate(useAverages):

                currentema = code.ema(bar, useAverages, period, prevema, smoothing=None)
                prevema = currentema

		print currentema

            if currentema >= upperLimit:
                print "Warning, possible attack!!!"

            useAverages.popleft()
            useAverages.append(currentema)
            #print 'Current: ' + str(useAverages)

        except KeyboardInterrupt:

            print " \n *** So long and thanks for all the fish! *** "
            break
