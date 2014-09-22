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
			self.upperLimit=0.4
			self.lowerLimit=0.1

			awk="{print $3;}'"
			awkString="awk '" + awk

			self.completeFlowList=[]

			self.switchProperties=SwitchProperties()
			self.interfacesList = self.switchProperties.getInterfaces()		

			print self.interfacesList

			self.feedbackDict=dict.fromkeys(['Notification','Flowlist','Interface'])

			for i in range(len(self.interfacesList)):				
				flowIntDict = dict.fromkeys(['interfaceName','dpid','flowList'])
				flowIntDict['interfaceName']= self.interfacesList[i]['name']
				flowIntDict['dpid']= self.interfacesList[i]['dpid']
				flowIntDict['flowList']=[]					
				self.completeFlowList.append(flowIntDict)
		
			self.msgSender = FeedbackMessage(self.aVersion, self.aPriority, self.controllerIp, self.flowFencePort)
			
		#toDo: This method should: Create a thread to handle that congestion report that applies local control and reports congestion and bad flows to controller
		def congestionDetected(self, interfaceDict, flowList):

			#Control variable to avoid sending multiple process		
			if self.controlInProcess == 0:

				print "Interface Dict: " + str(interfaceDict)
				self.feedbackDict['Notification']="Congestion"
				self.feedbackDict['Flowlist']=flowList
				self.feedbackDict['Interface']=dict.fromkeys(['capacity','dpid'])
				self.feedbackDict['Interface']['capacity']=interfaceDict['capacity']
				self.feedbackDict['Interface']['dpid']=interfaceDict['dpid']
				self.notificationMessage = json.dumps(str(self.feedbackDict))
				print "flow list: " + str(flowList)
				print 'Message sent: ' + self.notificationMessage

				self.msgSender.sendMessage(self.notificationMessage, self.controllerIp, self.flowFencePort)
				self.msgSender.closeConnection()

				self.controlInProcess = 1

		def congestionCeased(self, dpid):

			if self.controlInProcess == 1:			
			
				#Congestion Detected, sent notification to controller			
				self.actionDict['Notification']="Uncongestion"

				self.notificationMessage = json.dumps(str(self.actionDict) +str(interfaceDict) + str(flowList))
				
				self.msgSender.sendMessage(self.feedbackMsg, self.controllerIp, self.flowFencePort)
				self.msgSender.closeConnection()
				self.controlInProcess = 0			

		def getInstance(self):
			return ApplicationSwitch()

if __name__=="__main__":

	code=ApplicationSwitch()
	code.linkState=FlowMonitor(code.samples, code.period, code.intervalTime, code.upperLimit, code.lowerLimit)
	code.linkState.startMonitoring()
	
