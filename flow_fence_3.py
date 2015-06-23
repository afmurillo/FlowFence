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
import statistics as st
import time
from random import randint
from pox.lib.recoco import Timer



LOG = core.getLogger()
CONTROLLER_IP = '10.1.4.1'
switch_states = []
# in bits, obtained experimentally using TCP - Iperf
capacity = 16000000				 
#bw_for_new_flows = 0.0
remaining_bw = 100000000 
num_flows = 0
alfa =1.0
response_port = 23456
server_target = '10.1.2.1/32'
check_policy_time = 30
bad_flow_count_th = 0.9

# toDo: CHECK THIS VALUE!!!
min_sla = 100

class ServerSocket(Thread):

	""" Class that listens for switch messages """
	def __init__(self, connections):
		Thread.__init__(self)
		self.sock = None
		self.connections = connections						#dpdid of the switch

	def run(self):
		self.sock = socket.socket()
		host = CONTROLLER_IP
		port = 12345               							# Reserve a port for own communication btwn switches and controller
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
		#self.waiting_flow_stats = []

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

		elif message['Notification'] == 'QueuesFull':			
			self.handle_queues_full(message['Interface']['dpid'], self.myconnections, self.src_address, message)			


	def handle_congestion_notification(self, dpid):
		""" Upon reception of a congestion notification, requests for flow stats in the congestioned switch """
		dpid = dpid[:len(dpid)-1]
                dpid = dpid[len(dpid)-12:]
                #print 'Received dpid: ' + str(dpid)

		# We leave the 10% to handle new flows, during congestion.

		# Request flow stats from switch
		#print "dpid parameter: " + str(dpid)
		switch=dict.fromkeys(['dpid', 'flow_stats', 'wait_flag', 'drop_policy', 'bw_policy'])
		switch['drop_policy'] = 'Random'
		switch['bw_policy'] = 'Penalty'
		switch['dpid'] = dpid		
		switch['wait_flag'] = 0
		switch['flow_stats'] = []
		switch_states.append(switch)

		for connection in self.myconnections:
			connection_dpid = connection.dpid
			#print "Connection dpid: " + str(connection_dpid)
			dpid_str = dpidToStr(connection_dpid)
			dpid_str = dpid_str.replace("-", "")
			#print 'Real dpid_str: ' + dpid_str
			if dpid == dpid_str:
				connection.send(of.ofp_stats_request(body=of.ofp_flow_stats_request()))
				print 'Flow stats requets sent to: ' + str(connection)

	@classmethod
	def handle_queues_full(cls, dpid, connections, switch_addresss, message):
		# todo IMPLEMENT THIS!
		for i in range(len(switch_states)):
			if dpid == switch_states['dpid']:
				if switch_states[i]['drop_policy'] == 'Random':
					# Select and index at random
					drop_index = randint(0,len(switch_states[i]['flow_stats']))
					drop_flow = switch_states[i]['flow_stats'][drop_index]

				elif switch_states[i]['drop_policy'] == 'MOF': 	
					#sorted_flows = sorted(switch_states[i]['flow_stats'], key=lambda k[i]['flow_stats']: k[i]['flow_stats']['reportedBw']) 
					drop_index = randint(0,len(switch_states[i]['flow_stats']))
					drop_flow = sorted_flows[-1]

					# 1. Sort the flow_stats list
					# Get the index = 1

		my_match = of.ofp_match(dl_type = 0x800,nw_src=drop_flow['nw_src'],nw_dst=drop_flow['nw_dst'])
		msg = of.ofp_flow_mod(command=of.OFPFC_DELETE)
		msg.priority = 65535

		send_command_to_switch(dpid, msg)

		msg = of.ofp_flow_mod()
		msg.priority = 65535
		msg.idle_timeout = 0
		msg.hard_timeout = 0

		send_command_to_switch(dpid, msg)


	@classmethod
	def send_command_to_switch(dpid, msg):
		for connection in connections:
			connection_dpid = connection.dpid
			dpid_str = dpidToStr(connection_dpid)
			dpid_str = dpid_str.replace("-", "")
			#print 'Real dpid_str: ' + dpid_str
			if dpid == dpid_str:
				connection.send(msg)
				#print 'Sent to: ' + str(connection)
				#print 'Well...done'


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
		send_command_to_switch(dpid, msg)
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

def request_flows_stats_timer(connection, switch_index):

	connection.send(of.ofp_stats_request(body=of.ofp_flow_stats_request()))
	switch_states[switch_index]['wait_flag'] = 1

	return

def get_bw_flow_list(flow_list, indexes_to_process):

	flow_bw_list = []
	num_flows = 0

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
			acc_bw = acc_bw + float(flow_list[processing_indexes[i]]['byte_count']/flow_list[processing_indexes[i]]['duration_sec'])

		# Expressed in bits
		flow_bw_dictt['reportedBw'] = acc_bw * 8
		flow_bw_list.append(flow_bw_dictt)
		num_flows = num_flows + 1

		for i in range(len(processing_indexes)):
			indexes_to_process.remove(processing_indexes[i])

		return flow_bw_list

def _handle_flowstats_received (event):

	""" Calculates bw for each flow """

	global flow_stats_reply_time
	flow_stats_reply_time = time.time() - notification_time

	#flow_list = flow_stats_to_list(event.stats)
	sending_dpid = event.connection.dpid
	sending_address = event.connection.sock.getpeername()[0]

	bad_flows = 0
	flow_bw_list = []

	dpid = str(dpidToStr(event.dpid))

	# Get indexes of flow_list
	print "Flow stats received from: " , dpid
	dpid_str = dpid.replace("-", "")
	print "Sending dpid: ", sending_dpid
	
	for i in range(len(switch_states)):

		print "switch stats dpid: ", switch_states[i]['dpid']
		remaining_bw = 100000000	

		if (switch_states[i]['wait_flag'] == 0) and (switch_states[i]['dpid'] == dpid_str):
				# First print to make sure we're doing it alright
			# 1. Store in the switch state dict list
			# 2. Request again the flow stats
			#switch_states[i]['flow_stats']  = flow_stats_to_list(event.stats)
			print "First flow stats received"
			#switch_states[i]['wait_flag'] = 1

			flow_list = flow_stats_to_list(event.stats)
			indexes_to_process = [flow_index for flow_index, flow in enumerate(flow_list) if str(flow['match']['nw_dst'])==server_target]

			switch_states[i]['flow_stats'] = get_bw_flow_list(flow_list, indexes_to_process)
			print "Flow stats: "  + str(switch_states[i]['flow_stats'])
			Timer(5, request_flows_stats_timer, recurring = False, args=[event.connection, i])

		if (switch_states[i]['wait_flag']) == 1 and (switch_states[i]['dpid'] == dpid_str):			
			print "Second flow stats received"
			# Process the flows
			# We should 1. Mark the flow stats flag as 0 again
			#		    2. store in a temporal variable the flow stats, and for recurrent flows, update flow bw 
			switch_states[i]['wait_flag'] = 0
			flow_list = flow_stats_to_list(event.stats)
			indexes_to_process = [flow_index for flow_index, flow in enumerate(flow_list) if str(flow['match']['nw_dst'])==server_target]
			current_flow_stats = get_bw_flow_list(flow_list, indexes_to_process)
			#new_flows_indexes = []
			#stopped_flows_indexes = []
			print "Flow stats " + str(current_flow_stats)

			for j in range(len(current_flow_stats)):
				# Flow still exists, getting bw/s
				for k in range(len(switch_states[i]['flow_stats'])):
					if (current_flow_stats[j]['nw_src'] == switch_states[i]['flow_stats'][k]['nw_src']) and (current_flow_stats[j]['nw_src'] == switch_states[i]['flow_stats'][k]['nw_src']):
						switch_states[i]['flow_stats'][k]['reportedBw'] = current_flow_stats[j]['reportedBw'] - switch_states[i]['flow_stats'][k]['reportedBw']
						break

					# If it wasn't in k-1 and k we could have a) flow ceased b) flow is a new one
					#if (not any(src['nw_src'] ==  current_flow_stats[j]['nw_src'] for src in switch_states[i]['flow_stats'])) and ((not any(dst['nw_dst'] ==  current_flow_stats[j]['nw_dst'] for dst in switch_states[i]['flow_stats']))):
					# New flow does not exist in the old flow stats, append it
					#new_flows_indexes.append(j)
					#continue

			#for j in range(len(switch_states[i]['flow_stats'])):
			#if (not any(src['nw_src'] ==  switch_states[i]['flow_stats'][j]['nw_src'] for src in current_flow_stats)) and ((not any(dst['nw_dst'] ==  switch_states[i]['flow_stats'][j]['nw_dst'] for dst in current_flow_stats))):
			# New flow does not exist in the old flow stats, append it
			#stopped_flows_indexes(j)
			#continue				

			# Append new flows
			#for j in range(len(new_flows_indexes)):
			#switch_states[i]['flow_stats'].append(current_flow_stats[new_flows_indexes[j]])

			# Remove the flows that stopped from the global flow list
			#for j in range(len(stopped_flows_indexes)):
			#del switch_states[i]['flow_stats'][stopped_flows_indexes[j]]


			num_flows = len(switch_states[i]['flow_stats'])	
			# Good flows
			bad_flows_indexes = []
			if (switch_states[i]['bw_policy'] == 'Penalty'):
				for j in range(num_flows):
					switch_states[i]['flow_stats'][j]['goodBehaved'] = classiy_flows(capacity, switch_states[i]['flow_stats'][j]['reportedBw'], num_flows)

					# only for udp Iperf debugging purposes!
					#if flow_bw_list[i]['nw_src'] == '10.1.1.3':
					#flow_bw_list[i]['goodBehaved'] = True
					#else:
					#flow_bw_list[i]['goodBehaved'] = False

					if switch_states[i]['flow_stats'][j]['goodBehaved'] == True:
						switch_states[i]['flow_stats'][j]['bw'] = switch_states[i]['flow_stats'][j]['reportedBw']

	                    		if switch_states[i]['flow_stats'][j]['bw'] > 900000000:
						switch_states[i]['flow_stats'][j]['bw'] = 900000000 
						remaining_bw = remaining_bw -  switch_states[i]['flow_stats'][j]['bw']
					else:
						bad_flows = bad_flows + 1
						bad_flows_indexes.append(j)

				# Bad Flows
				for j in range(len(bad_flows_indexes)):
					switch_states[i]['flow_stats'][bad_flows_indexes[j]]
					switch_states[i]['flow_stats'][bad_flows_indexes[j]]['reportedBw'] = assign_bw_to_bad_behaved(capacity, remaining_bw, bad_flows, num_flows, switch_states[i]['flow_stats'][bad_flows_indexes[j]]['reportedBw'], alfa)
					if switch_states[i]['flow_stats'][bad_flows_indexes[j]]['reportedBw'] > 3000000:
						switch_states[i]['flow_stats'][bad_flows_indexes[j]]['reportedBw'] = 3000000
						#print "Bad behaved flow bw " +  str(flow_bw_list[i]['bw'])
						remaining_bw = remaining_bw - switch_states[i]['flow_stats'][bad_flows_indexes[j]]['reportedBw']

				# Give remmaining bw between good flows
				if bad_flows < num_flows:
					extra_bw = remaining_bw/(num_flows - bad_flows)
					for j in range(len(num_flows)):
						if switch_states[i]['flow_stats'][j]['goodBehaved'] == True:
				    			switch_states[i]['flow_stats'][j]['bw'] =  switch_states[i]['flow_stats'][j]['bw'] + extra_bw
				                #print "Good behaved flow bw: " + str(flow_bw_list[i]['bw']
						if switch_states[i]['flow_stats'][j]['bw'] > 900000000:
							switch_states[i]['flow_stats'][j]['bw'] = 900000000

			if (switch_states[i]['bw_policy'] == 'Equal'):
				simple_bw = capacity/num_flows
				for j in range(num_flows):
					switch_states[i]['flow_stats'][j]['bw'] = simple_bw

			queues_dict = dict.fromkeys(['Response','dpid','bw_list'])
			queues_dict['dpid'] = sending_dpid
			queues_dict['Response'] = "Decrement"
			queues_dict['bw_list'] = switch_states[i]['flow_stats']

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
	#print "Capacity: " + str(capacity)
	if estimated_bw > (capacity/num_flows):
		return False
	else:
		return True

def assign_bw_to_bad_behaved(capacity, remaining_bw, num_bad_flows, num_total_flows, flow_rate, alfa):
	""" Assigns bw to each flow """
	#return flow_rate - (1 - math.exp(-(flow_rate-(capacity/num_total_flows))))*alfa*flow_rate
 	print "Bad behaved with: " + "capacity :" + str(capacity) + " remaining bw: " + str(remaining_bw) + " bad flows: " + str(num_bad_flows)
	print "Total flows: " + str(num_total_flows) + "flow rate : " + str(flow_rate) + "alfa: " + str(alfa)
	fair_rate = capacity/num_total_flows
	bad_fair_rate = capacity / num_bad_flows
	#print "remaining_bw: " + str(remaining_bw)
	#print "num bad flows : " + str(num_bad_flows)
	#print "fair rate: " + str(fair_rate)
	#print "bad fair: " + str(bad_fair_rate)
	#print "flow rate: " + str (flow_rate)
	bw = bad_fair_rate - (1 - math.exp( - (flow_rate - fair_rate) )) * alfa * bad_fair_rate
	return bw

def check_policies():

	if not switch_states:
		return
	else:
		for i in range(len(switch_states)):
			bad_flow_count = 0
			num_flows = len(switch_states[i]['flow_stats'])
			bw_list = []
			for j in range(num_flows):

				bw_list.append(switch_states[i]['flow_stats'][j]['bw'])
				if switch_states[i]['flow_stats'][j]['goodBehaved'] == False:
					bad_flow_count = bad_flow_count + 1

			if bad_flow_count >= float(num_flows*bad_flow_count_th):
				# Number of bad flows is 90% of the total flow count, switch policy
				switch_states[i]['bw_policy'] = 'Equal'
			else:
				switch_states[i]['bw_policy'] = 'Penalty'

			if len(bw_list) > 1:
				bw_dev = st.stdev(bw_list)
				if bw_dev < min_sla:
					switch_states[i]['drop_policy'] = 'MOF'				
				else:
					switch_states[i]['drop_policy'] = 'Random'

def launch ():
	""" First method called """
	print "FlowFence launched"
	core.registerNew(ConnectTest)
	core.openflow.addListenerByName("FlowStatsReceived", _handle_flowstats_received)
	Timer(check_policy_time, check_policies, recurring = True)
