from FeedbackMessage import *
from LinkMonitoring import *
import json
import subprocess

class ApplicationSwitch:

		"""
		Main class that runs in OpenFlow switches for FlowFence
		"""

		def __init__(self):

			#Controller message parameters
			self.aVersion=1
			self.controllerIp='10.1.4.1'		
			self.aType='request'
			self.aProto='udp'
			self.someFlags='none'
			self.aPriority=0
			self.aLink = '10.1.2.2'
			self.flowFencePort = 12345

			self.Ka='\x08+\xe1\x8d\x85\x86E\x02?H.K\xf7@\xe5\xeb'
			self.Kab='\x17\xf4\x9c\x98\xd6\x84\xcb\xcf\xe6\x93\x11\xe2\xbaI\xdfM'

			#Link monitoring parameters
			something=1
			self.controlInProcess=0

			self.samples=10
			self.period=3
			self.intervalTime=1.0
			self.upperLimit=60
			self.lowerLimit=40
			self.incremental=5000000
			self.decremental=0.5
			self.interface='eth0'

                        awk="{print $3;}'"
                        awkString="awk '" + awk

			self.dpid=subprocess.check_output('ovs-vsctl list bridge ' + self.interface + 'br | grep datapath_id | ' + awkString, shell=True)

			self.msgSender = FeedbackMessage(self.aVersion, self.aType, self.aProto, self.someFlags, self.aPriority, self.controllerIp, self.flowFencePort)

		def congestionDetected(self, dpid):

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
			

		def getInstance(self):
			return ApplicationSwitch()

if __name__=="__main__":

		code=ApplicationSwitch()
		
		print 'LALALALA dpid: ' + str(code.dpid)
		
		code.linkState=LinkMonitoring(code.dpid, code.samples, code.period, code.intervalTime, code.upperLimit, code.lowerLimit, code.incremental, code.decremental)		
		code.linkState.startMonitoring()

		#Check how to stop it properly
		while True:
			try:

				a=1

			except KeyboardInterrupt:

				print " \n *** So long and thanks for all the fish! *** "
				code.linkState.stopMonitoring()
				self.msgSender.closeConnection()
        		break        	
