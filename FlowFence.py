from pox.core import core
import pox.openflow.libopenflow_01 as of
from pox.lib.revent import *
from pox.lib.util import dpidToStr
from pox.lib.addresses import EthAddr, IPAddr
from collections import namedtuple
from pox.topology.topology import Switch, Entity
from pox.lib.revent import EventMixin
import pox.lib.packet as pkt

from threading import Thread
from collections import deque

import os
import string, sys, socket, json, subprocess
import thread 
import time
import math

"""
DoS Mitigation - FlowFence component
"""

#######################################

log = core.getLogger()
controllerIp = '10.1.4.1' 

############################	Here is the socket server ####
class server_socket(Thread):
	
	def __init__(self, connections):
		Thread.__init__(self)
		global received
		self.sock = None
		#self.status =-1			
		self.connections = connections						#dpdi of the switch

	def run(self):
		self.sock = socket.socket()         				# Create a socket object
		host = controllerIp									
		port = 12345               							# Reserve a port for own communication btwn switches and controller
		#log.info("Binding to listen for switch messages")
		print "Binding to listen for switch messages"
		self.sock.bind((host, port))        				# Bind to the port
		self.sock.listen(5)                	 				# Now wait for client connection.

		while True:												
			try:			
				client, addr = self.sock.accept()				# Establish connection with client
				data = client.recv(1024)						# Get data from the client 
				print 'Message from', addr 						# Print a message confirming 
				data_treatment = handle_message(data,self.connections, addr)	# Call the thread to work with the data received
				data_treatment.setDaemon(True)					# Set the thread as a demond
				data_treatment.start()							# Start the thread

			except KeyboardInterrupt:
				print "\nCtrl+C was hitten, stopping server"
				client.close()
				break
		
#########################
class handle_message(Thread):

	def __init__(self,received,connections, addr):
		Thread.__init__(self)
		self.received = received
		self.myconnections = connections
		self.srcAddress = addr[0]
		self.alfa=1
		self.responsePort=23456
		self.bwForNewFlows=0.1
		print self.myconnections

	def run(self):
	
		print 'message from ' + str(self.srcAddress)

		try:
			message = eval(json.loads(self.received))
			print "Message received " + str(message)
		except:
			print "An error ocurred processing the incoming message"

		print "Type of message " + str(message['Notification'])
	
		if message['Notification'] == 'Congestion':
			self.handleCongestionNotification(message, self.srcAddress)
		elif message['Notification'] == 'Uncongestion':
			self.handleUncongestionNotification(message, self.srcAddress)
		elif message['Notification'] == 'QueuesDone':
			self.handleFlowsRedirection(message['Interface']['dpid'],self.myconnections, self.srcAddress, message)

	def handleCongestionNotification(self, notificationMessage, switchAddres):
		# Algorithm: Classify good and bad flows, assign bandwidth fo good flows, assign band fo bad flows, assign remaining band
		# Bad flows bw: assignedBw(j,i)=avaliableBw/badFlows - (1 -exp( - (rates(i)-capacityOverN) ) )*alfas(j)*rates(i);

		flowBwList=[]
		flowBwDict=dict.fromkeys(['nw_src','nw_dst','goodBehaved','bw'])
		badFlows=0
		bwForBadFlows=0

		# We leave the 10% to handle new flows, during congestion.
		remainingBw = notificationMessage['Interface']['capacity']*(1-self.bwForNewFlows)

		# Good Flows
		for i in range(len(notificationMessage['Flowlist'])):
			flowBwDict['nw_src'] = notificationMessage['Flowlist'][i]['nw_src']
			flowBwDict['nw_dst'] = notificationMessage['Flowlist'][i]['nw_dst']
			flowBwDict['goodBehaved'] = self.classifyFlows(notificationMessage['Interface']['capacity'], notificationMessage['Flowlist'][i]['arrivalRate'],len(notificationMessage['Flowlist']))

			if flowBwDict['goodBehaved'] == True:
				flowBwDict['bw']= notificationMessage['Flowlist'][i]['arrivalRate']
				flowBwDict['bw'] = 300000
				remainingBw = remainingBw - notificationMessage['Flowlist'][i]['arrivalRate']
			else:
				badFlows=badFlows+1

			flowBwList.append(flowBwDict)

		bwForBadFlows=remainingBw

		# Bad Flows
		for i in range(len(notificationMessage['Flowlist'])):
			if flowBwDict['goodBehaved'] == False:
				flowBwList[i]['bw']= self.assignBwToBadBehaved(bwForBadFlows, badFlows, notificationMessage['Interface']['capacity'], len(notificationMessage['Flowlist']), notificationMessage['Flowlist'][i]['arrivalRate'], self.alfa)
				flowBwList[i]['bw'] = 300000
				# Here we should check witch switches also handle the bad behaved flow to apply the same control, in the simplest topology (Dumb-bell), it is not neccesary
				remainingBw = remainingBw - flowBwList[i]['bw']

		# Give remmaining bw between good flows
		for i in range(len(notificationMessage['Flowlist'])):
			if flowBwDict['goodBehaved'] == True:
				flowBwList[i]['bw']= remainingBw/(len(notificationMessage['Flowlist']) - badFlows)
				flowBwList[i]['bw'] = 300000
		
		print "Calculated Bandwidth: " + str(flowBwList)

		queuesDict = dict.fromkeys(['Response'],['bwList'])
		queuesDict['Interface'] = notificationMessage['Interface']['name']
		queuesDict['Response'] = "Decrement"
		queuesDict['bwList'] = flowBwList

		responseMessage = json.dumps(str(queuesDict))

		print "Response Message sent: " + str(responseMessage)

		responseSocket = self.createSocket()
		self.sendMessage(responseSocket,switchAddres, self.responsePort, responseMessage)
		self.closeConnection(responseSocket)
	
	def sendMessage(self, aSocket, ipAddress, port, aMessage):
		aSocket.connect((ipAddress, port))
		aSocket.send(aMessage)	
	
	def closeConnection(self, aSocket):				
		aSocket.close()

	def createSocket(self):
		return socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		
	def handleUnCongestionNotification(self, notificationMessage, switchAddres):
		print "Congestion stopped"
	
	#In further versions, other classification methods could be used
	def classifyFlows(self, capacity, estimatedBw, numFlows):
		if (estimatedBw>capacity/numFlows):
			return False
		else:
			return True

	def assignBwToBadBehaved(self, avaliableBw, numBadFlows, capacity, numTotalFlows, flowRate, alfa):		
		#return avaliableBw/numBadFlows - (1 - math.exp(-(flowRate-(capacity/numTotalFlows))))*alfa*flowRate
		return 300000

	
	def handleFlowsRedirection(self, dpid, connections, switchAddress, message):

		print 'message from ' + str(switchAddress)
		print 'Connections ' + str(dir(connections))

		dpid = dpid[:len(dpid)-1]
		dpid = dpid[len(dpid)-12:]
		print 'Received dpid: ' + str(dpid)

		print "message to be used for redirection" + str(message)
		for i in range(len(message['Flowlist'])):

			# We only want to redirect outgoing flows
			if message['Flowlist'][i]['action'] != 'LOCAL':		
				#my_match = of.ofp_match(nw_src=message['Flowlist'][i]['nw_src'],nw_dst=message['Flowlist'][i]['nw_dst'])
				my_match = of.ofp_match(dl_type = 0x800,nw_src=message['Flowlist'][i]['nw_src'],nw_dst=message['Flowlist'][i]['nw_dst'])

				print "Flow Match: " + str(my_match)
				msg = of.ofp_flow_mod()
				msg.match = my_match
				msg.priority=65535
		
				# There is a bug here, the error it shows reads "can't convert argument to int" when try to send the message
				# If the actions are omitted (aka we order to drop the packets with match, we get no error)
				msg.actions.append(of.ofp_action_enqueue(port=int(message['Flowlist'][i]['action'].split(':')[1]), queue_id=int(message['QueueList'][i]['queueId'])))
				
				print "Flow mod message: " + str(msg)

	  	              	#toDo: Check a better way to do this
				print "dpid parameter: " + str(dpid)
	                	for connection in connections:
        	        		connectionDpid=connection.dpid
					print "Connection dpid: " + str(connectionDpid)
                			dpidStr=dpidToStr(connectionDpid)
	                		dpidStr=dpidStr.replace("-", "")
        	        		print 'Real dpidStr: ' + dpidStr

	                		if dpid == dpidStr:
        	        			connection.send(msg)
						print 'Sent to: ' + str(connection)
						print 'Well...done'	


class connect_test(EventMixin):	
	# Waits for OpenFlow switches to connect and makes them learning switches.
	#Global variables of connect_test subclass
	#global received
	def __init__(self):
		self.listenTo(core.openflow)
		log.debug("Received connection from switch")
		print("Received connection from switch")
		self.myconnections=[]		# a list of the connections
		socket_server=server_socket(self.myconnections)	# send it to the socket with the connection 
		socket_server.setDaemon(True)		# establish the thread as a deamond, this will make to close the thread with the main program
		socket_server.start()				# starting the thread

	def _handle_ConnectionUp (self, event):
		print "switch dpid " + str(event.dpid) #it prints the switch connection information, on the screen
		print "Hex dpid: " + str(dpidToStr(event.dpid))
		self.myconnections.append(event.connection)	# will pass as a reference to above

#######################################


def launch ():
	#core.openflow.addListenerByName("FlowStatsReceived", listarFluxosIp)
	print "FlowFence launched"
	core.registerNew(connect_test)


