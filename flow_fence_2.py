"""
DoS Mitigation - FlowFence component

Module running in the SDN controller
Receives congestion notifications, calculates bandwidth for each flow, sends commands to apply bw
"""

from pox.core import core
import pox.openflow.libopenflow_01 as of
from pox.lib.revent import *
from pox.lib.util import dpidToStr
from pox.lib.revent import EventMixin


from pox.openflow.of_json import *

from threading import Thread

import socket
import json
import math
import time

LOG = core.getLogger()
CONTROLLER_IP = '10.1.4.1'

class ServerSocket(Thread):

	""" Class that listens for switch messages """
	def __init__(self, connections):
		Thread.__init__(self)
		self.sock = None
		self.connections = connections						#dpdi of the switch

	def run(self):
		self.sock = socket.socket()
		host = CONTROLLER_IP
		port = 12345               							# Reserve a port for own communication btwn switches and controller
		#log.info("Binding to listen for switch messages")
		#print "Binding to listen for switch messages"
		self.sock.bind((host, port))        				# Bind to the port
		self.sock.listen(5)

		while True:
			try:

				client, addr = self.sock.accept()
				data = client.recv(4096)
				#print 'Message from', addr
				data_treatment = HandleMessage(data,self.connections, addr)
				data_treatment.setDaemon(True)
				data_treatment.start()
			except KeyboardInterrupt:
				print "\nCtrl+C was hitten, stopping server"
				client.close()
				break

class HandleMessage(Thread):

	""" Handles messages sent by SDN switchhes """

	def __init__(self,received,connections, addr):
		Thread.__init__(self)
		self.received = received
		self.myconnections = connections
		self.src_address = addr[0]
		self.alfa = 1
		self.response_port = 23456
		self.bw_for_new_flows = 0.1
		#print self.myconnections

	def run(self):

		print 'message from ' + str(self.src_address)

		try:
			message = eval(json.loads(self.received))
			#print "Message received " + str(message)
		except:
			print "An error ocurred processing the incoming message"

		if message['Notification'] == 'Congestion':
			global notification_time
			notification_time = time.time()

			self.handle_congestion_notification(message['Interface']['dpid'])
		elif message['Notification'] == 'QueuesDone':
			global queues_done_time
			queues_done_time = time.time() - flow_stats_reply_time

			self.handle_flows_redirection(message['Interface']['dpid'], self.myconnections, self.src_address, message)

	def handle_congestion_notification(self, dpid):
		""" Upon reception of a congestion notification, requests for flow stats in the congestioned switch """
                dpid = dpid[:len(dpid)-1]
                dpid = dpid[len(dpid)-12:]
                #print 'Received dpid: ' + str(dpid)

		# We leave the 10% to handle new flows, during congestion.

		# Request flow stats from switch
		#print "dpid parameter: " + str(dpid)
		for connection in self.myconnections:
			connection_dpid = connection.dpid
			#print "Connection dpid: " + str(connection_dpid)
			dpid_str = dpidToStr(connection_dpid)
			dpid_str = dpid_str.replace("-", "")
			#print 'Real dpid_str: ' + dpid_str
			if dpid == dpid_str:
				connection.send(of.ofp_stats_request(body=of.ofp_flow_stats_request()))
				#print 'Flow stats requets sent to: ' + str(connection)

	@classmethod
	def handle_flows_redirection(cls, dpid, connections, switch_addresss, message):

		""" Sends flow mod messages to redirect flows to created queues """
		#print 'message from ' + str(switch_addresss)
		#print 'Connections ' + str(dir(connections))

		dpid = dpid[:len(dpid)-1]
		dpid = dpid[len(dpid)-12:]
		#print 'Received dpid: ' + str(dpid)

		#print "message to be used for redirection" + str(message)

		msg = of.ofp_flow_mod(command=of.OFPFC_DELETE)
		msg.priority = 65535

		#print "dpid parameter: " + str(dpid)
		for connection in connections:
			connection_dpid = connection.dpid
			dpid_str = dpidToStr(connection_dpid)
			dpid_str = dpid_str.replace("-", "")
			#print 'Real dpid_str: ' + dpid_str
			if dpid == dpid_str:
				connection.send(msg)
				#print 'Sent to: ' + str(connection)
				#print 'Well...done'

		for i in range(len(message['bw_list'])):

			# We only want to redirect outgoing flows
			if message['bw_list'][i]['action'] != 'OFPP_LOCAL':

				my_match = of.ofp_match(dl_type = 0x800,nw_src=message['bw_list'][i]['nw_src'],nw_dst=message['bw_list'][i]['nw_dst'])

				#print "Flow Match: " + str(my_match)
				msg = of.ofp_flow_mod()
				msg.match = my_match
				msg.priority = 65535
				msg.idle_timeout = 0
    				msg.hard_timeout = 0
				msg.actions.append(of.ofp_action_enqueue(port=int(message['bw_list'][i]['action']), queue_id=int(message['queue_list'][i]['queueId'])))

				#print "Flow mod message: " + str(msg)

	  	              	#toDo: Check a better way to do this
				#print "dpid parameter: " + str(dpid)
	                	for connection in connections:
        	        		connection_dpid=connection.dpid
					#print "Connection dpid: " + str(connection_dpid)
                			dpid_str=dpidToStr(connection_dpid)
	                		dpid_str=dpid_str.replace("-", "")
        	        		#print 'Real dpid_str: ' + dpid_str

	                		if dpid == dpid_str:
        	        			connection.send(msg)
							 	global flow_mod_time
							 	flow_mod_time = time.time() - queues_done_time

						print "Notification time: " + str(notification_time)
						print "Flow stats reply: " + str(flow_stats_reply_time)
						print "Queues done time: " + str(queues_done_time)
						print "Flow mode time :" + str(flow_mod_time) 
						#print 'Sent to: ' + str(connection)
						#print 'Well...done'

class ConnectTest(EventMixin):

	""" Waits for OpenFlow switches to connect and makes them learning switches. """

	def __init__(self):
		self.listenTo(core.openflow)
		LOG.debug("Received connection from switch")
		#print "Received connection from switch"
		self.myconnections = []		# a list of the connections
		socket_server=ServerSocket(self.myconnections)	# send it to the socket with the connection
		socket_server.setDaemon(True)		# establish the thread as a deamond, this will make to close the thread with the main program
		socket_server.start()				# starting the thread

	def _handle_ConnectionUp(self, event):
		""" Event that handles connection events """
		print "switch dpid " + str(event.dpid) #it prints the switch connection information, on the screen
		print "Hex dpid: " + str(dpidToStr(event.dpid))
		self.myconnections.append(event.connection)	# will pass as a reference to above

#######################################

def _handle_flowstats_received (event):

	""" Calculates bw for each flow """

	global flow_stats_reply_time
	flow_stats_reply_time = time.time() - notification_time

	flow_list = flow_stats_to_list(event.stats)
	sending_dpid = event.connection.dpid
	sending_address = event.connection.sock.getpeername()[0]

	bad_flows = 0
	flow_bw_list = []

	# in bits, obtained experimentally using TCP - Iperf
	capacity = 16000000				 
	#bw_for_new_flows = 0.0
	remaining_bw = 100000000 
	num_flows = 0
	alfa =1.0
	response_port = 23456

	# Get indexes of flow_list
	indexes_to_process = [flow_index for flow_index, flow in enumerate(flow_list) if str(flow['match']['nw_dst'])=='10.1.2.1/32']

	#print "Flow List indexes: " + str(indexes_to_process)

	while len(indexes_to_process) > 0 :

		#print "Remaining indexes: " + str(indexes_to_process)

		# we should add a line to ignore if nw_dst != '10.1.2.2'
		# Get src of first flow
		nw_src = str(flow_list[indexes_to_process[0]]['match']['nw_src'])

		#print "Processing flows with nw_src: " + str(nw_src)

		processing_indexes = [flow_index for flow_index, flow in enumerate(flow_list) if str(flow['match']['nw_src']) == nw_src ]

		#print "Processing indexes: " + str(processing_indexes)

		flow_bw_dictt=dict.fromkeys(['nw_src', 'nw_dst', 'reportedBw', 'goodBehaved', 'bw', 'action'])
		flow_bw_dictt['nw_src'] = str(flow_list[processing_indexes[0]]['match']['nw_src'])
		flow_bw_dictt['nw_dst'] = str(flow_list[processing_indexes[0]]['match']['nw_dst'])
		flow_bw_dictt['action'] = flow_list[processing_indexes[0]]['actions'][0]['port']
		acc_bw = 0

		for i in range(len(processing_indexes)):
			acc_bw = acc_bw + flow_list[processing_indexes[i]]['byte_count']

		# Expressed in bits
		flow_bw_dictt['reportedBw'] = acc_bw * 8
		flow_bw_list.append(flow_bw_dictt)
		num_flows = num_flows + 1

		for i in range(len(processing_indexes)):
			indexes_to_process.remove(processing_indexes[i])

	# Good flows
	for i in range(len(flow_bw_list)):
		flow_bw_list[i]['goodBehaved'] = classiy_flows(capacity, flow_bw_list[i]['reportedBw'], num_flows)

		# only for udp Iperf debugging purposes!
		if flow_bw_list[i]['nw_src'] == '10.1.1.3':
			flow_bw_list[i]['goodBehaved'] = True
		#else:
		#flow_bw_list[i]['goodBehaved'] = False

		if flow_bw_list[i]['goodBehaved'] == True:
			flow_bw_list[i]['bw'] = flow_bw_list[i]['reportedBw']

                        if flow_bw_list[i]['bw'] > 900000000:
                                flow_bw_list[i]['bw'] = 900000000 

			remaining_bw = remaining_bw -  flow_bw_list[i]['bw']
		else:
			bad_flows = bad_flows+1

	# Bad Flows
	for i in range(len(flow_bw_list)):
		if flow_bw_list[i]['goodBehaved'] == False:
			flow_bw_list[i]['bw']= assign_bw_to_bad_behaved(capacity, remaining_bw, bad_flows, num_flows, flow_bw_list[i]['reportedBw'], alfa)
                        if flow_bw_list[i]['bw'] > 3000000:
				flow_bw_list[i]['bw'] = 3000000
			#print "Bad behaved flow bw " +  str(flow_bw_list[i]['bw'])
			remaining_bw = remaining_bw - flow_bw_list[i]['bw']

	# Give remmaining bw between good flows
	if bad_flows < num_flows:
		extra_bw = remaining_bw/(num_flows - bad_flows)
	        for i in range(len(flow_bw_list)):
        	        if flow_bw_list[i]['goodBehaved'] == True:
                	        flow_bw_list[i]['bw'] =  flow_bw_list[i]['bw'] + extra_bw
                        	#print "Good behaved flow bw: " + str(flow_bw_list[i]['bw'])
	                        if flow_bw_list[i]['bw'] > 900000000:
        	                        flow_bw_list[i]['bw'] = 900000000

	queues_dict = dict.fromkeys(['Response','dpid','bw_list'])
	queues_dict['dpid'] = sending_dpid
	queues_dict['Response'] = "Decrement"
	queues_dict['bw_list'] = flow_bw_list

	response_message = json.dumps(str(queues_dict))

	#print "Response Message sent: " + str(response_message)

	response_socket = create_socket()
	send_message(response_socket,sending_address, response_port, response_message)
	close_connection(response_socket)

def create_socket():
	""" Creates a socket """
	return socket.socket(socket.AF_INET, socket.SOCK_STREAM)

def send_message(a_socket, ip_address, port, a_message):

	""" Sends a message to a SDN switch """
	a_socket.connect((ip_address, port))
	a_socket.send(a_message)

def close_connection(a_socket):
	""" Closes a connection """
	a_socket.close()

def classiy_flows(capacity, estimated_bw, num_flows):
	""" Classifies flows """
	#print "Num Flows: " + str(num_flows)
	3print "Capacity: " + str(capacity)
	if estimated_bw > (capacity/num_flows):
		return False
	else:
		return True

def assign_bw_to_bad_behaved(capacity, remaining_bw, num_bad_flows, num_total_flows, flow_rate, alfa):
	""" Assigns bw to each flow """
	#return flow_rate - (1 - math.exp(-(flow_rate-(capacity/num_total_flows))))*alfa*flow_rate
	fair_rate = capacity/num_total_flows
	bad_fair_rate = capacity / num_bad_flows
	#print "remaining_bw: " + str(remaining_bw)
	#print "num bad flows : " + str(num_bad_flows)
	#print "fair rate: " + str(fair_rate)
	#print "bad fair: " + str(bad_fair_rate)
	#print "flow rate: " + str (flow_rate)
	bw = bad_fair_rate - (1 - math.exp( - (flow_rate - fair_rate) )) * alfa * bad_fair_rate
	return bw

def launch ():
	""" First method called """
	print "FlowFence launched"
	core.registerNew(ConnectTest)
	core.openflow.addListenerByName("FlowStatsReceived", _handle_flowstats_received)
