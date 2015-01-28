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
                                data = client.recv(4096)                                                # Get data from the client
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

class ApplicationSwitch_2:

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
                        self.upperLimit=100
                        self.lowerLimit=50

                        awk="{print $3;}'"
                        awkString="awk '" + awk


                        self.completeFlowList=[]

                        self.switchProperties=SwitchProperties()
                        self.interfacesList = self.switchProperties.getInterfaces()

                        self.applicationPort=23456

                        print self.interfacesList

                        feedbackDict=dict.fromkeys(['Notification','Interface'])

                        for i in range(len(self.interfacesList)):
                                flowIntDict = dict.fromkeys(['interfaceName','dpid'])
                                flowIntDict['interfaceName']= self.interfacesList[i]['name']
                                flowIntDict['dpid']= self.interfacesList[i]['dpid']
                                self.completeFlowList.append(flowIntDict)

                        self.msgSender = FeedbackMessage(self.aVersion, self.aPriority, self.controllerIp, self.flowFencePort)
			
			
		#toDo: This method should: Create a thread to handle that congestion report that applies local control and reports congestion and bad flows to controller
		def congestionDetected(self, interfaceDict):

			#Control variable to avoid sending multiple process		
			if self.controlInProcess == 0:

				print "Interface Dict: " + str(interfaceDict)
                                feedbackDict=dict.fromkeys(['Notification','Interface'])

				feedbackDict['Notification']="Congestion"				
				feedbackDict['Interface']=dict.fromkeys(['capacity','dpid','name'])
				feedbackDict['Interface']['capacity']=interfaceDict['capacity']
				feedbackDict['Interface']['dpid']=interfaceDict['dpid']
                                feedbackDict['Interface']['name']=interfaceDict['name']                                
				self.notificationMessage = json.dumps(str(feedbackDict))				
				print 'Message sent: ' + self.notificationMessage

				self.msgSender.sendMessage(self.notificationMessage, self.controllerIp, self.flowFencePort)
				self.msgSender.closeConnection()

				self.controlInProcess = 1

		def congestionCeased(self, dpid):

			if self.controlInProcess == 1:			
			
				print "Congestion ceased"

                def queuesReady(self, interfaceDict, bwList, queueList):

                        print "Interface Dict: " + str(interfaceDict)

                        feedbackDict=dict.fromkeys(['Notification','QueueList','Interface','bwList'])
                        feedbackDict['Notification']="QueuesDone"
                        feedbackDict['QueueList']=queueList
                        feedbackDict['Interface']=dict.fromkeys(['capacity','dpid'])
                        feedbackDict['Interface']['capacity']=interfaceDict['capacity']
                        feedbackDict['Interface']['dpid']=interfaceDict['dpid']
                        feedbackDict['Interface']['name']=interfaceDict['name']
                        feedbackDict['bwList']=bwList

                        self.notificationMessage = json.dumps(str(feedbackDict))
                        
                        print 'Message sent: ' + self.notificationMessage

                        self.msgSender.sendMessage(self.notificationMessage, self.controllerIp, self.flowFencePort)
                        self.msgSender.closeConnection()                


		def messageFromController(self,message,srcAddress):

			print "Raw message received: " + str(message)
			messageDict = eval(json.loads(message))

			print "Message Received: " + str(messageDict)
                        # En caso que el mensaje sea una indicacion de congestion, debemos preparar las filas y reportar que han sido inicializadas exitosamente
                        # Luego recibiremos un flowmod enviando los flujos a las filas respectivas
                        if messageDict['Response'] == "Decrement":
				self.linkState.createQueues(messageDict)

		def getInstance(self):
			return ApplicationSwitch()

if __name__=="__main__":

	code=ApplicationSwitch_2()

        code.listenSocket = SwitchSocket(code, code.listenPort)
        code.listenSocket.setDaemon(True)
        code.listenSocket.start()

	code.linkState=FlowMonitor(code.samples, code.period, code.intervalTime, code.upperLimit, code.lowerLimit)
	# Here we could put the MAGI event :D
	print "Init Finished"
	code.linkState.startMonitoring()
