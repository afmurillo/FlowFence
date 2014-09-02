from FeedbackMessage import *
from FlowMonitor import *
from SwitchProperties import *

import json
import subprocess

class ApplicationSwitch:

		"""
		Main class that runs in OpenFlow switches for FlowFence
		"""

		def __init__(self):

			#Controller message parameters
			self.aVersion=2.0
			self.controllerIp='10.1.4.1'		
	
			#todo: ???
			self.aType='request'

			#todo What's this?
			self.aProto='udp'
			self.someFlags='none'
			self.aPriority=0

			#todo: Handle this!
			self.aLink = '10.1.2.2'
			self.flowFencePort = 12345

			self.Ka='\x08+\xe1\x8d\x85\x86E\x02?H.K\xf7@\xe5\xeb'
			self.Kab='\x17\xf4\x9c\x98\xd6\x84\xcb\xcf\xe6\x93\x11\xe2\xbaI\xdfM'

			#Link monitoring parameters			
			self.controlInProcess=0

			self.samples=10
			self.period=3
			self.intervalTime=1.0
			self.upperLimit=8.4
			self.lowerLimit=0.6

			awk="{print $3;}'"
			awkString="awk '" + awk

			self.switchProperties=SwitchProperties()
			self.interfacesList = self.switchProperties.getInterfaces()		

			for i in range(len(self.interfacesList)):
				flowIntDict = dict.fromkeys(['interfaceName'],['flowList'])
				flowIntDict['interfaceName']= self.interfacesList[i]['name']
				flowIntDict['dpid']= self.interfacesList[i]['dpid']
				flowIntDict['flowList']=[]					
				self.completeFlowList.append(flowIntDict)
		
			self.msgSender = FeedbackMessage(self.aVersion, self.aType, self.aProto, self.someFlags, self.aPriority, self.controllerIp, self.flowFencePort)
			
		#toDo: This method should: Create a thread to handle that congestion report that applies local control and reports congestion and bad flows to controller
		def congestionDetected(self, dpid, flowList):
		
			for i in range(len(self.interfacesList)):
				if dpid == completeFlowList[i]['dpid']:
					#Here we should calculate the arrival rates for each flow, each flow is an element of flowList	
					completeFlowList[i]['flowList']=flowList
					for j in range(len(completeFlowList[i]['flowList'])):
						completeFlowList[i]['flowList'][j]['arrivalRate'] = self.calculateArrivalRate()
						#TODO: IMPLEMENT CALCULATE ARRIVAL RATE!!!
			

			if self.controlInProcess == 0:

				#Congestion Detected, sent notification to controller			
				self.decrMsg = self.msgSender.createDecrFeedback(self.Ka, self.Kab, self.dpid, self.aVersion, self.aType, self.aProto, self.aPriority, self.someFlags, self.controllerIp, self.aLink)			
				self.feedbackMsg = json.dumps(str(self.decrMsg))
				print 'Message sent: ' + self.feedbackMsg
				#print 'Sending congestion message...'
				self.msgSender.sendMessage(self.feedbackMsg, self.controllerIp, self.flowFencePort)
				self.msgSender.closeConnection()
				#print 'Message sent'
				self.controlInProcess = 1
				#toDo: When we should send a report again?				

		def congestionCeased(self, dpid):

			if self.controlInProcess == 1:			

				#Congestion Detected, sent notification to controller			
				self.incrMsg = self.msgSender.createIncrFeedback(self.Ka, self.dpid, self.aVersion, self.aType, self.aProto, self.aPriority, self.someFlags, self.controllerIp, self.aLink)			
				self.feedbackMsg = json.dumps(str(self.incrMsg))

				#print 'Sending congestion ending message...'
				self.msgSender.sendMessage(self.feedbackMsg, self.controllerIp, self.flowFencePort)
				self.msgSender.closeConnection()
				#print 'Message sent'
				self.controlInProcess = 0
				#toDo: When we should send a report again?				
				#toDo: controlInProcess is a semaphore variable? how to handle it? make a state diagram
			

		def self.calculateArrivalRate()
			return 1

		def getInstance(self):
			return ApplicationSwitch()

if __name__=="__main__":

	code=ApplicationSwitch()
	print 'Current dpids: '
	for i in range(len(code.interfacesList)):

		print "Dpid: " + str(code.interfacesList[i]['dpid'])

	code.linkState=FlowMonitor(code.samples, code.period, code.intervalTime, code.upperLimit, code.lowerLimit)
	code.linkState.startMonitoring()
	
	#toDo: Check how to stop it properly

	while True:
		try:
			a=1

		except KeyboardInterrupt:
			print " \n *** So long and thanks for all the fish! *** "
			code.linkState.stopMonitoring()
			self.msgSender.closeConnection()
			break        	
