from pox.core import core
import pox.openflow.libopenflow_01 as of
from pox.lib.revent import *
from pox.lib.util import dpidToStr
from pox.lib.addresses import EthAddr, IPAddr
from collections import namedtuple
from pox.topology.topology import Switch, Entity
from pox.lib.revent import EventMixin
from pox.lib.recoco import Timer

import pox.lib.packet as pkt

from pox.openflow.of_json import *

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
				data = client.recv(4096)						# Get data from the client 
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

		#print "Type of message " + str(message['Notification'])
	
		if message['Notification'] == 'Congestion':
			self.handleCongestionNotification(message['Interface']['dpid'],message, self.srcAddress)
		elif message['Notification'] == 'QueuesDone':
			self.handleFlowsRedirection(message['Interface']['dpid'],self.myconnections, self.srcAddress, message)

	def handleCongestionNotification(self, dpid, notificationMessage, switchAddres):
		# Algorithm: Classify good and bad flows, assign bandwidth fo good flows, assign band fo bad flows, assign remaining band
		# Bad flows bw: assignedBw(j,i)=avaliableBw/badFlows - (1 -exp( - (rates(i)-capacityOverN) ) )*alfas(j)*rates(i);

		flowBwList=[]
		badFlows=0
		bwForBadFlows=0

                dpid = dpid[:len(dpid)-1]
                dpid = dpid[len(dpid)-12:]
                print 'Received dpid: ' + str(dpid)

		# We leave the 10% to handle new flows, during congestion.
		remainingBw = notificationMessage['Interface']['capacity']*(1-self.bwForNewFlows)

		# Request flow stats from switch
		print "dpid parameter: " + str(dpid)
		for connection in self.myconnections:
			connectionDpid=connection.dpid
			print "Connection dpid: " + str(connectionDpid)
			dpidStr=dpidToStr(connectionDpid)
			dpidStr=dpidStr.replace("-", "")
			print 'Real dpidStr: ' + dpidStr
			if dpid == dpidStr:
				connection.send(of.ofp_stats_request(body=of.ofp_flow_stats_request()))
				print 'Flow stats requets sent to: ' + str(connection)				
		
	def handleFlowsRedirection(self, dpid, connections, switchAddress, message):

		print 'message from ' + str(switchAddress)
		print 'Connections ' + str(dir(connections))

		dpid = dpid[:len(dpid)-1]
		dpid = dpid[len(dpid)-12:]
		print 'Received dpid: ' + str(dpid)

		print "message to be used for redirection" + str(message)
		for i in range(len(message['bwList'])):

			# We only want to redirect outgoing flows
			if message['bwList'][i]['action'] != 'OFPP_LOCAL':		
				
				my_match = of.ofp_match(dl_type = 0x800,nw_src=message['bwList'][i]['nw_src'],nw_dst=message['bwList'][i]['nw_dst'])

				print "Flow Match: " + str(my_match)
				msg = of.ofp_flow_mod()
				msg.match = my_match
				msg.priority=65535
		
				# There is a bug here, the error it shows reads "can't convert argument to int" when try to send the message
				# If the actions are omitted (aka we order to drop the packets with match, we get no error)
				msg.actions.append(of.ofp_action_enqueue(port=int(message['bwList'][i]['action']), queue_id=int(message['QueueList'][i]['queueId'])))
				
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

def _handle_flowstats_received (event):

	flowList = flow_stats_to_list(event.stats)
	sendingDpid = event.connection.dpid
	sendingAddress = event.connection.sock.getpeername()[0]

	print "Sending address " + str(sendingAddress)
	
	# check how to dynamically do this

	badFlows=0
	bwForBadFlows=0
	flowBwList=[]
	capacity = 10000000
	bwForNewFlows = 0.1
	remainingBw = capacity*(1-bwForNewFlows)	
	numFlows = 0
	alfa = 1
	responsePort = 23456

	# Get indexes of flowList
	indexesToProcess = [flowIndex for flowIndex, flow in enumerate(flowList) ]

	#print "Flow List indexes: " + str(indexesToProcess)

	while len(indexesToProcess) > 0 :

		#print "Remaining indexes: " + str(indexesToProcess)

		# we should add a line to ignore if nw_dst != '10.1.2.2'
		# Get src of first flow
		nw_src = flowList[indexesToProcess[0]]['match']['nw_src']

		#print "Processing flows with nw_src: " + str(nw_src)

		processingIndexes = [flowIndex for flowIndex, flow in enumerate(flowList) if flow['match']['nw_src'] == nw_src ]

		#print "Processing indexes: " + str(processingIndexes)

		flowBwDict=dict.fromkeys(['nw_src','nw_dst','reportedBw','goodBehaved','bw', 'action'])
		flowBwDict['nw_src'] = flowList[processingIndexes[0]]['match']['nw_src']
		flowBwDict['nw_dst'] = flowList[processingIndexes[0]]['match']['nw_dst']
		flowBwDict['action'] = flowList[processingIndexes[0]]['actions'][0]['port']	

		accBw = 0

		for i in range(len(processingIndexes)):
			accBw = accBw + flowList[processingIndexes[i]]['byte_count']

		flowBwDict['reportedBw'] = accBw		
		flowBwList.append(flowBwDict)
		numFlows = numFlows + 1
		
		for i in range(len(processingIndexes)):
			indexesToProcess.remove(processingIndexes[i])
		
	# Good flows
	for i in range(len(flowBwList)):	
		flowBwList[i]['goodBehaved'] = classifyFlows(capacity, flowBwList[i]['reportedBw'],numFlows)	
	
		if flowBwList[i]['goodBehaved'] == True:	
			flowBwList[i]['bw']= flowBwList[i]['reportedBw']
			remainingBw = remainingBw -  flowBwList[i]['reportedBw']
		else:
			badFlows=badFlows+1

	# Bad Flows
	bwForBadFlows=remainingBw
	for i in range(len(flowBwList)):	
		if flowBwList[i]['goodBehaved'] == False:
			flowBwList[i]['bw']= assignBwToBadBehaved(bwForBadFlows, badFlows, capacity, numFlows, flowBwList[i]['reportedBw'], alfa)
			print "Bad behaved flow bw " +  str(flowBwList[i]['bw'])
			remainingBw = remainingBw - flowBwList[i]['bw']

	# Give remmaining bw between good flows
	extraBw = remainingBw/(numFlows - badFlows)

	for i in range(len(flowBwList)):
		if flowBwList[i]['goodBehaved'] == True:
			flowBwList[i]['bw']=  flowBwList[i]['bw'] + extraBw
			print "Good behaved flow bw: " + str(flowBwList[i]['bw'])		

	print "Calculated Bandwidth: " + str(flowBwList)	

	queuesDict = dict.fromkeys(['Response','dpid','bwList'])
	queuesDict['dpid'] = sendingDpid
	queuesDict['Response'] = "Decrement"
	queuesDict['bwList'] = flowBwList

	responseMessage = json.dumps(str(queuesDict))

	print "Response Message sent: " + str(responseMessage)

	responseSocket = createSocket()
	sendMessage(responseSocket,sendingAddress, responsePort, responseMessage)
	closeConnection(responseSocket)

def createSocket():
	return socket.socket(socket.AF_INET, socket.SOCK_STREAM)

	
def sendMessage(aSocket, ipAddress, port, aMessage):
	aSocket.connect((ipAddress, port))
	aSocket.send(aMessage)	

def closeConnection(aSocket):				
	aSocket.close()



#In further versions, other classification methods could be used
def classifyFlows( capacity, estimatedBw, numFlows):
	if (estimatedBw>capacity/numFlows):
		return False
	else:
		return True

def assignBwToBadBehaved( avaliableBw, numBadFlows, capacity, numTotalFlows, flowRate, alfa):		
	return avaliableBw/numBadFlows - (1 - math.exp(-(flowRate-(capacity/numTotalFlows))))*alfa*flowRate
	
def launch ():
	#core.openflow.addListenerByName("FlowStatsReceived", listarFluxosIp)
	print "FlowFence launched"
	core.registerNew(connect_test)
	core.openflow.addListenerByName("FlowStatsReceived", _handle_flowstats_received) 


