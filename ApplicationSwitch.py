from FeedbackMessage import *
from FlowMonitor import *
from SwitchProperties import *

import json
import subprocess

import socket
import sys
from time import *
from threading import Thread


class SwitchSocket(Thread):

        def __init__(self, reportObject, applicationPort):
                Thread.__init__(self)
                self.applicationPort = applicationPort
		self.reportObject=reportObject

        def run(self):
                self.sock = socket.socket()     # Create a socket object
                host = subprocess.check_output("ifconfig | grep 10.1.4 | awk '{print $2;}'", shell=True).split(':')[1].split('\n')[0]
                self.sock.bind((host, self.applicationPort))                                    # Bind to the port
                self.sock.listen(5)

                while True:
                        try:
                                client, addr = self.sock.accept()                               # Establish connection with client
                                data = client.recv(1024)                                                # Get data from the client
                                print 'Message from', addr                                              # Print a message confirming
                                data_treatment = handle_message(self.reportObject, data, addr)    # Call the thread to work with the data received
                                data_treatment.setDaemon(True)                                  # Set the thread as a demond
                                data_treatment.start()                                                  # Start the thread
                        except KeyboardInterrupt:
                                print "\nCtrl+C was hitten, stopping server"
                                client.close()
                                break


class handle_message(Thread):

        def __init__(self,reportObject, received, addr):
                Thread.__init__(self)
                self.received = received
                self.srcAddress = addr[0]
                self.responsePort=23456
                self.bwForNewFlows=0.1
		self.reportObject = reportObject

        def run(self):
                self.reportObject.messageFromController(self.received,self.srcAddress)

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
                        self.listenPort = 23456

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

                        self.applicationPort=23456

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
				
				self.completeFlowList = flowList

				print "Interface Dict: " + str(interfaceDict)
				self.feedbackDict['Notification']="Congestion"
				self.feedbackDict['Flowlist']=flowList
				self.feedbackDict['Interface']=dict.fromkeys(['capacity','dpid','name'])
				self.feedbackDict['Interface']['capacity']=interfaceDict['capacity']
				self.feedbackDict['Interface']['dpid']=interfaceDict['dpid']
                                self.feedbackDict['Interface']['name']=interfaceDict['name']
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

                def queuesReady(self, interfaceDict, flowList, queueList):

                        print "Interface Dict: " + str(interfaceDict)
                        self.feedbackDict['Notification']="QueuesDone"
                        self.feedbackDict['Flowlist']=flowList
                        self.feedbackDict['QueueList']=queueList
                        self.feedbackDict['Interface']=dict.fromkeys(['capacity','dpid'])
                        self.feedbackDict['Interface']['capacity']=interfaceDict['capacity']
                        self.feedbackDict['Interface']['dpid']=interfaceDict['dpid']
                        self.feedbackDict['Interface']['name']=interfaceDict['name']
                        self.notificationMessage = json.dumps(str(self.feedbackDict))
                        
                        print 'Message sent: ' + self.notificationMessage

                        self.msgSender.sendMessage(self.notificationMessage, self.controllerIp, self.flowFencePort)
                        self.msgSender.closeConnection()                


		def messageFromController(self,message,srcAddress):
			print "Message Received: " + str(message)
                        # En caso que el mensaje sea una indicación de congestion, debemos preparar las filas y reportar que han sido inicializadas exitosamente
                        # Luego recibiremos un flowmod enviando los flujos a las filas respectivas
                        if message['Response'] == "Decrement":
                                self.linkState.createQueues(message)

		def getInstance(self):
			return ApplicationSwitch()

if __name__=="__main__":

	code=ApplicationSwitch()

        code.listenSocket = SwitchSocket(code, code.listenPort)
        code.listenSocket.setDaemon(True)
        code.listenSocket.start()

	code.linkState=FlowMonitor(code.samples, code.period, code.intervalTime, code.upperLimit, code.lowerLimit)
	code.linkState.startMonitoring()
