# Copyright 2011-2012 James McCauley
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at:
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
An L2 learning switch.

It is derived from one written live for an SDN crash course.
It is somwhat similar to NOX's pyswitch in that it installs
exact-match rules for each flow.
"""

from pox.core import core
import pox.openflow.libopenflow_01 as of
from pox.lib.util import dpid_to_str
from pox.lib.util import str_to_bool
from pox.lib.revent import *
from pox.lib.revent import EventMixin
from pox.openflow.of_json import *
import time

from threading import Thread
from threading import Lock


import socket
import json
import math
import statistics as st
import time
from random import randint
from operator import itemgetter
from pox.lib.recoco import Timer

log = core.getLogger()

# We don't want to flood immediately when a switch connects.
# Can be overriden on commandline.
_flood_delay = 0

LOG = core.getLogger()
CONTROLLER_IP = '10.1.4.1'
switch_states = []
# in bits, obtained experimentally using TCP - Iperf
capacity = 100000000
#bw_for_new_flows = 0.0
remaining_bw = 100000000
num_flows = 0
alfa =0.9
response_port = 23456
server_target = '10.1.2.1/32'
check_policy_time = 30
bad_flow_count_th = 0.9

# toDo: CHECK THIS VALUE!!!
min_sla = 10000000
flow_update_time = 5

global updating
updating = 0

controlled = 0

class LearningSwitch (object):
  """
  The learning switch "brain" associated with a single OpenFlow switch.

  When we see a packet, we'd like to output it on a port which will
  eventually lead to the destination.  To accomplish this, we build a
  table that maps addresses to ports.

  We populate the table by observing traffic.  When we see a packet
  from some source coming from some port, we know that source is out
  that port.

  When we want to forward traffic, we look up the desintation in our
  table.  If we don't know the port, we simply send the message out
  all ports except the one it came in on.  (In the presence of loops,
  this is bad!).

  In short, our algorithm looks like this:

  For each packet from the switch:
  1) Use source address and switch port to update address/port table
  2) Is transparent = False and either Ethertype is LLDP or the packet's
     destination address is a Bridge Filtered address?
     Yes:
        2a) Drop packet -- don't forward link-local traffic (LLDP, 802.1x)
            DONE
  3) Is destination multicast?
     Yes:
        3a) Flood the packet
            DONE
  4) Port for destination address in our address/port table?
     No:
        4a) Flood the packet
            DONE
  5) Is output port the same as input port?
     Yes:
        5a) Drop packet and similar ones for a while
  6) Install flow table entry in the switch so that this
     flow goes out the appopriate port
     6a) Send the packet out appropriate port
  """
  def __init__ (self, connection, transparent):
    # Switch we'll be adding L2 learning switch capabilities to
    self.connection = connection
    self.transparent = transparent

    # Our table
    self.macToPort = {}

    # We want to hear PacketIn messages, so we listen
    # to the connection
    connection.addListeners(self)

    # We just use this to know when to log a helpful message
    self.hold_down_expired = _flood_delay == 0

    #log.debug("Initializing LearningSwitch, transparent=%s",
    #          str(self.transparent))

  def _handle_PacketIn (self, event):
    """
    Handle packet in messages from the switch to implement above algorithm.
    """

    packet = event.parsed

    def flood (message = None):
      """ Floods the packet """
      msg = of.ofp_packet_out()
      if time.time() - self.connection.connect_time >= _flood_delay:
        # Only flood if we've been connected for a little while...

        if self.hold_down_expired is False:
          # Oh yes it is!
          self.hold_down_expired = True
          log.info("%s: Flood hold-down expired -- flooding",
              dpid_to_str(event.dpid))

        if message is not None: log.debug(message)
        #log.debug("%i: flood %s -> %s", event.dpid,packet.src,packet.dst)
        # OFPP_FLOOD is optional; on some switches you may need to change
        # this to OFPP_ALL.
        msg.actions.append(of.ofp_action_output(port = of.OFPP_FLOOD))
      else:
        pass
        #log.info("Holding down flood for %s", dpid_to_str(event.dpid))
      msg.data = event.ofp
      msg.in_port = event.port
      self.connection.send(msg)

    def drop (duration = None):
      """
      Drops this packet and optionally installs a flow to continue
      dropping similar ones for a while
      """
      if duration is not None:
        if not isinstance(duration, tuple):
          duration = (duration,duration)
        msg = of.ofp_flow_mod()
        msg.match = of.ofp_match.from_packet(packet)
        msg.idle_timeout = duration[0]
        msg.hard_timeout = duration[1]
        msg.buffer_id = event.ofp.buffer_id
        self.connection.send(msg)
      elif event.ofp.buffer_id is not None:
        msg = of.ofp_packet_out()
        msg.buffer_id = event.ofp.buffer_id
        msg.in_port = event.port
        self.connection.send(msg)

    tcpp = event.parsed.find('tcp')	
    ip_dst = 0
    if tcpp:
	    ip_packet = event.parsed.find("ipv4")
	    ip_dst = ip_packet.dstip

    if (controlled == 1) and (ip_dst == '10.1.2.1'):
      return

    self.macToPort[packet.src] = event.port # 1

    if not self.transparent: # 2
      if packet.type == packet.LLDP_TYPE or packet.dst.isBridgeFiltered():
        drop() # 2a
        return

    if packet.dst.is_multicast:
      flood() # 3a
    else:
      if packet.dst not in self.macToPort: # 4
        flood("Port for %s unknown -- flooding" % (packet.dst,)) # 4a
      else:
        port = self.macToPort[packet.dst]
        if port == event.port: # 5
          # 5a
          log.warning("Same port for packet from %s -> %s on %s.%s.  Drop."
              % (packet.src, packet.dst, dpid_to_str(event.dpid), port))
          drop(10)
          return
        # 6
        log.debug("installing flow for %s.%i -> %s.%i" %
                  (packet.src, event.port, packet.dst, port))
        msg = of.ofp_flow_mod()
        msg.match = of.ofp_match.from_packet(packet, event.port)
        msg.idle_timeout = 10
        msg.hard_timeout = 10
        msg.priority = 30000
        msg.actions.append(of.ofp_action_output(port = port))
        msg.data = event.ofp # 6a

        dpid = str(dpidToStr(event.dpid))
        dpid_str = dpid.replace("-", "")

        # Create a new entry in our flow state table for the new flow
        for i in range(len(switch_states)):
          if (switch_states[i]['dpid'] == dpid_str) and (msg.match.dl_type == 'IP'):
	    flow_bw_dictt=dict.fromkeys(['nw_src', 'nw_dst', 'dl_src','dl_dst','dl_vlan','dl_vlan_pcp','dl_type','nw_tos','nw_proto','tp_src','tp_dst','reportedBw', 'goodBehaved', 'bw', 'action'])
	    flow_bw_dictt['goodBehaved'] = False
            flow_bw_dictt['nw_src'] = str(msg.match.nw_src)
            flow_bw_dictt['nw_dst'] = str(msg.match.nw_dst)
            flow_bw_dictt['dl_src'] = msg.match.dl_src
            flow_bw_dictt['dl_dst'] = msg.match.dl_dst
            flow_bw_dictt['dl_vlan'] = msg.match.dl_vlan
            #flow_bw_dictt['dl_vlan_pcp'] = msg.match.dl_vlan_pcp
            flow_bw_dictt['dl_type'] = msg.match.dl_type
            flow_bw_dictt['nw_tos'] = msg.match.nw_tos
            flow_bw_dictt['nw_proto'] = msg.match.nw_proto
            flow_bw_dictt['tp_src'] = msg.match.tp_src
            flow_bw_dictt['tp_dst'] = msg.match.tp_dst
            flow_bw_dictt['action'] = port
	    #flow_bw_dictt['in_port'] = msg.match.in_port
	    #print "Built packet in dict: ", flow_bw_dictt
            switch_states[i]['flow_stats'].append(flow_bw_dictt)
         
        self.connection.send(msg)


class flow_fence (object):
  """
  Waits for OpenFlow switches to connect and makes them learning switches.
  """
  def __init__ (self, transparent):
    core.openflow.addListeners(self)
    self.transparent = transparent
    #self.listenTo(core.openflow)
    LOG.debug("Received connection from switch")
    #print "Received connection from switch"
    self.myconnections = []   # a list of the connections
    socket_server=ServerSocket(self.myconnections)  # send it to the socket with the connection
    socket_server.setDaemon(True)   # establish the thread as a deamond, this will make to close the thread with the main program
    socket_server.start()       # starting the thread

  def _handle_ConnectionUp (self, event):
    log.debug("Connection %s" % (event.connection,))
    print "Connection received", event.connection
    self.myconnections.append(event.connection) # will pass as a reference to above    
    LearningSwitch(event.connection, self.transparent)

class ServerSocket(Thread):

  """ Class that listens for switch messages """
  def __init__(self, connections):
    Thread.__init__(self)
    self.sock = None
    self.connections = connections            #dpid of the switch

  def run(self):
    self.sock = socket.socket()
    host = CONTROLLER_IP
    port = 12345                            # Reserve a port for own communication btwn switches and controller
    self.sock.bind((host, port))                # Bind to the port
    self.sock.listen(5)

    while True:
      try:
        client, addr = self.sock.accept()
        data = client.recv(4096)
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

  def run(self):

    print 'message from ' + str(self.src_address)

    try:
      message = eval(json.loads(self.received))
    except:
      print "An error ocurred processing the incoming message"
      return

    if message['Notification'] == 'Congestion':
      global notification_time
      notification_time = time.time()

      self.handle_congestion_notification(self.myconnections, message['Interface']['dpid'])

    elif message['Notification'] == 'QueuesDone':
      global queues_done_time
      queues_done_time = time.time() - flow_stats_reply_time
      self.handle_flows_redirection(message['Interface']['dpid'], self.myconnections, self.src_address, message)

    elif message['Notification'] == 'QueuesFull':     
      self.handle_queues_full(message['Interface']['dpid'], self.myconnections, self.src_address, message)      

  def handle_congestion_notification(self, connections, dpid):
    """ Upon reception of a congestion notification, requests for flow stats in the congestioned switch """
    dpid = dpid[:len(dpid)-1]
    dpid = dpid[len(dpid)-12:]

    switch=dict.fromkeys(['dpid', 'flow_stats', 'drop_policy', 'bw_policy'])
    switch['drop_policy'] = 'Random'
    switch['bw_policy'] = 'Penalty'
    switch['dpid'] = dpid   
    switch['flow_stats'] = []
    switch_states.append(switch)
    Timer(flow_update_time, self.update_flow_stats, recurring = True, args=[dpid, connections])
    msg = of.ofp_stats_request(body=of.ofp_flow_stats_request())
    print 'Flow stats requets sent to: ' + str(connections)   
    self.send_command_to_switch(dpid, connections, msg)
    
  def update_flow_stats(self, dpid, connections):
    global updating
    updating = 1
    #print "updating flows"
    msg = of.ofp_stats_request(body=of.ofp_flow_stats_request())
    self.send_command_to_switch(dpid, connections, msg)

  @classmethod
  def handle_queues_full(cls, dpid, connections, switch_addresss, message):

    # We need to perform 4 operations:
    # 1. Select a flow to be dropped according to our policy
    # 2. Delete the flow entry in the flowtable
    # 3. Send a command to remove that flow queue in th switch
    # 4. Delete the flow entry in the flow_stats dictionary

    for i in range(len(switch_states)):
      if dpid == switch_states['dpid']:
        if switch_states[i]['drop_policy'] == 'Random':
          # Select and index at random
          switch_index = i
          drop_index = randint(0,len(switch_states[i]['flow_stats']))
          drop_flow = switch_states[i]['flow_stats'][drop_index]

        elif switch_states[i]['drop_policy'] == 'MOF':  
          #sorted_flows = sorted(switch_states[i]['flow_stats'], key=lambda k[i]['flow_stats']: k[i]['flow_stats']['reportedBw']) 
          sorted_flows = sorted(switch_states[i]['flow_stats'], key=itemgetter('reportedBw'), reverse=True)
          switch_index = i
          #drop_index = randint(0,len(switch_states[i]['flow_stats']))
          drop_flow = sorted_flows[0]

          # 1. Sort the flow_stats list
          # Get the index = 1

    my_match = of.ofp_match(dl_type = 0x800,nw_src=drop_flow['nw_src'],nw_dst=drop_flow['nw_dst'])
    msg = of.ofp_flow_mod(command=of.OFPFC_DELETE)
    msg.priority = 65535

    cls.send_command_to_switch(dpid, connections, msg)

    msg = of.ofp_flow_mod()
    msg.priority = 65535
    msg.idle_timeout = 60
    #msg.hard_timeout = 60


    cls.send_command_to_switch(dpid, connections, msg)

    drop_flow

    queues_dict = dict.fromkeys(['Response','dpid','drop_flow'])
    queues_dict['dpid'] = dpid
    queues_dict['Response'] = "Delete_queue"
    queues_dict['drop_flow'] = drop_flow

    response_message = json.dumps(str(queues_dict))
    response_socket = create_socket()
    send_message(response_socket, sending_address, response_port, response_message)
    close_connection(response_socket)

    del switch_states[switch_index]['flow_stats'][drop_index] 

  @classmethod
  def send_command_to_switch(cls, dpid, connections, msg):
    for connection in connections:
      connection_dpid = connection.dpid
      dpid_str = dpidToStr(connection_dpid)
      dpid_str = dpid_str.replace("-", "")
      if dpid == dpid_str:
        #print "Sending message to switch: ", dpid
        #print "Message sent: ", msg
        #print "Message match: ", msg.match
        #print "Message actions: ",msg.actions

	lock = Lock()
	lock.acquire()
        try:
		connection.send(msg)
	finally:
		lock.release()


  @classmethod
  def handle_flows_redirection(cls, dpid, connections, switch_addresss, message):

    """ Sends flow mod messages to redirect flows to created queues """

    #print "Received message for flow redirection: ", message

    dpid = dpid[:len(dpid)-1]
    dpid = dpid[len(dpid)-12:]

    #msg = of.ofp_flow_mod(command=of.OFPFC_DELETE)
    #msg.priority = 65535

    #cls.send_command_to_switch(dpid, connections, msg)

    #dpid_a = str(dpidToStr(event.dpid))
    #dpid_str = dpid_a.replace("-", "")
    switch_index = 0
    # Create a new entry in our flow state table for the new flow
    for i in range(len(switch_states)):
	if switch_states[i]['dpid'] == dpid:
		#print "found switch"
		switch_index = i

    for i in range(len(message['bw_list'])):

      # We only want to redirect outgoing flows
      if message['bw_list'][i]['action'] != 'OFPP_LOCAL':

        for j in range(len(switch_states[switch_index]['flow_stats'])):
		if (message['bw_list'][i]['nw_src'] == switch_states[switch_index]['flow_stats'][j]['nw_src']) and (message['bw_list'][i]['nw_dst'] == switch_states[switch_index]['flow_stats'][j]['nw_dst']):
			flow_index = j
			break

	if ((switch_states[switch_index]['flow_stats'][flow_index]['nw_src'] == '10.1.1.3') or (switch_states[switch_index]['flow_stats'][flow_index]['nw_src'] == '10.1.1.13')):
	        my_match = of.ofp_match(dl_type = 0x800, \
	          dl_src = EthAddr(switch_states[switch_index]['flow_stats'][flow_index]['dl_src']), dl_dst = EthAddr(switch_states[switch_index]['flow_stats'][flow_index]['dl_dst']),\
        	  nw_src = switch_states[switch_index]['flow_stats'][flow_index]['nw_src'], nw_dst = switch_states[switch_index]['flow_stats'][flow_index]['nw_dst'], \
	          dl_vlan = switch_states[switch_index]['flow_stats'][flow_index]['dl_vlan'], \
		  #in_port = switch_states[switch_index]['flow_stats'][flow_index]['in_port'], \
	          nw_tos = switch_states[switch_index]['flow_stats'][flow_index]['nw_tos'], nw_proto = switch_states[switch_index]['flow_stats'][flow_index]['nw_proto'], \
	          tp_dst = switch_states[switch_index]['flow_stats'][flow_index]['tp_dst'])
	else:
		my_match = of.ofp_match(dl_type = 0x800, \
	          dl_src = EthAddr(switch_states[switch_index]['flow_stats'][flow_index]['dl_src']), dl_dst = EthAddr(switch_states[switch_index]['flow_stats'][flow_index]['dl_dst']),\
		  nw_src = switch_states[switch_index]['flow_stats'][flow_index]['nw_src'], nw_dst = switch_states[switch_index]['flow_stats'][flow_index]['nw_dst'], \
		  dl_vlan = switch_states[switch_index]['flow_stats'][flow_index]['dl_vlan'], \
		  #in_port = switch_states[switch_index]['flow_stats'][flow_index]['in_port'], \
		  nw_tos = switch_states[switch_index]['flow_stats'][flow_index]['nw_tos'], nw_proto = switch_states[switch_index]['flow_stats'][flow_index]['nw_proto'], \
		  tp_src = switch_states[switch_index]['flow_stats'][flow_index]['tp_src'], tp_dst = switch_states[switch_index]['flow_stats'][flow_index]['tp_dst'])


	#if ((switch_states[switch_index]['flow_stats'][flow_index]['nw_src'] == '10.1.1.3') or (switch_states[switch_index]['flow_stats'][flow_index]['nw_src'] == '10.1.1.13')):
	#msg = of.ofp_flow_mod(command=of.OFPFC_DELETE)
	#msg.priority = 65535
	#cls.send_command_to_switch(dpid, connections, msg)
		
	msg = of.ofp_flow_mod()
        msg.match = my_match
	#print "Match for flow: ", msg.match

        msg.priority = 65535
        msg.idle_timeout = 60
        msg.actions.append(of.ofp_action_enqueue(port=int(message['bw_list'][i]['action']), queue_id=int(message['queue_list'][i]['queueId'])))

	#print "Sending redirect"
	cls.send_command_to_switch(dpid, connections, msg)

    #if len(message['bw_list']) > capacity/min_sla:
    #if len(message['bw_list']) > capacity/min_sla:
    #self.handle_queues_full(dpid, connections, switch_addresss, message)

    controlled = 1      

def get_bw_flow_list(flow_list, indexes_to_process):

  flow_bw_list = []
  num_flows = 0

  while len(indexes_to_process) > 0 :

    # Get src of first flow
    #print "handling for flow: ", flow_list[indexes_to_process[0]]
    nw_src = str(flow_list[indexes_to_process[0]]['match']['nw_src'])

    processing_indexes = [flow_index for flow_index, flow in enumerate(flow_list) if str(flow['match']['nw_src']) == nw_src ]

    flow_bw_dictt=dict.fromkeys(['nw_src', 'nw_dst', 'dl_src','dl_dst','dl_vlan','dl_vlan_pcp','dl_type','nw_tos','nw_proto','tp_src','tp_dst','reportedBw', 'goodBehaved', 'bw', 'action'])
    flow_bw_dictt['nw_src'] = str(flow_list[processing_indexes[0]]['match']['nw_src'])
    flow_bw_dictt['nw_dst'] = str(flow_list[processing_indexes[0]]['match']['nw_dst']).split('/')[0]
    flow_bw_dictt['dl_src'] = flow_list[processing_indexes[0]]['match']['dl_src']
    flow_bw_dictt['dl_dst'] = flow_list[processing_indexes[0]]['match']['dl_dst']
    flow_bw_dictt['dl_vlan'] = flow_list[processing_indexes[0]]['match']['dl_vlan']
    #flow_bw_dictt['dl_vlan_pcp'] = flow_list[processing_indexes[0]]['match']['dl_vlan_pcp']
    flow_bw_dictt['dl_type'] = flow_list[processing_indexes[0]]['match']['dl_type']

    if 'nw_tos' in flow_list[processing_indexes[0]]['match']:
	flow_bw_dictt['nw_tos'] = flow_list[processing_indexes[0]]['match']['nw_tos']

    flow_bw_dictt['nw_proto'] = flow_list[processing_indexes[0]]['match']['nw_proto']
    if 'tp_src' in flow_list[processing_indexes[0]]['match']:
	flow_bw_dictt['tp_src'] = flow_list[processing_indexes[0]]['match']['tp_src']

    if 'tp_dst' in flow_list[processing_indexes[0]]['match']:
        flow_bw_dictt['tp_dst'] = flow_list[processing_indexes[0]]['match']['tp_dst']

    flow_bw_dictt['action'] = flow_list[processing_indexes[0]]['actions'][0]['port']
    #flow_bw_dictt['in_port'] = flow_list[processing_indexes[0]]['match']['in_port']

    acc_bw = 0

    for i in range(len(processing_indexes)):
      duration = float(flow_list[processing_indexes[i]]['duration_sec'] + float(flow_list[processing_indexes[i]]['duration_nsec'] /1000000000))
      if duration > 0:
        acc_bw = acc_bw + float(flow_list[processing_indexes[i]]['byte_count']/duration)
        #print "Acc bw: ", acc_bw
      else: 
        acc_bw = acc_bw + flow_list[processing_indexes[i]]['byte_count']
    # Expressed in bits
    flow_bw_dictt['reportedBw'] = acc_bw * 8
    flow_bw_list.append(flow_bw_dictt)
    num_flows = num_flows + 1

    for i in range(len(processing_indexes)):
      indexes_to_process.remove(processing_indexes[i])

  return flow_bw_list

def assign_bw(flow_stats, policy):

  num_flows = len(flow_stats) 
  bad_flows_indexes = []
  bad_flows = 0
  remaining_bw = 100000000

  if (policy == 'Penalty'):
    # Good flows
    print "Bw Policy: Penalty"
    for j in range(num_flows):
	flow_stats[j]['goodBehaved'] = classiy_flows(capacity, flow_stats[j]['reportedBw'], num_flows)

	if flow_stats[j]['nw_src'] == '10.1.1.3':
		flow_stats[j]['goodBehaved'] = True
	else:
		flow_stats[j]['goodBehaved'] = False

	if flow_stats[j]['goodBehaved'] == True:
		#print "Giving bw to good behaved"
		flow_stats[j]['bw'] = flow_stats[j]['reportedBw']
		#print "good behaved flow bw: ", flow_stats[j]['bw']
	else:
		bad_flows = bad_flows + 1
		bad_flows_indexes.append(j)

	if flow_stats[j]['bw'] > 90000000:
	        flow_stats[j]['bw'] = 90000000 
        	remaining_bw = remaining_bw - flow_stats[j]['bw']

    # Bad Flows
    for j in range(len(bad_flows_indexes)):
	flow_stats[bad_flows_indexes[j]]
	flow_stats[bad_flows_indexes[j]]['bw'] = assign_bw_to_bad_behaved(capacity, remaining_bw, bad_flows, num_flows, flow_stats[bad_flows_indexes[j]]['reportedBw'], alfa)

	if flow_stats[bad_flows_indexes[j]]['bw'] < 20000:
		flow_stats[bad_flows_indexes[j]]['bw'] = 20000
	        #print "Bad behaved flow bw " +  str(flow_bw_list[i]['bw'])
        	remaining_bw = remaining_bw - flow_stats[bad_flows_indexes[j]]['bw']

    # Give remmaining bw between good flows
    if bad_flows < num_flows:
	extra_bw = remaining_bw/(num_flows - bad_flows)
	for j in range(num_flows):
		if flow_stats[j]['goodBehaved'] == True:
			flow_stats[j]['bw'] =  flow_stats[j]['bw'] + extra_bw
			#print "Good behaved flow bw: " + str(flow_bw_list[i]['bw']
		        if flow_stats[j]['bw'] > 90000000:
				flow_stats[j]['bw'] = 90000000

    if (policy == 'Equal'):
	print "Bw policy: Equal"
	simple_bw = capacity/num_flows
	for j in range(num_flows):
		flow_stats[j]['bw'] = simple_bw

  return flow_stats


def _handle_flowstats_received (event):

  """ Calculates bw for each flow """

  global flow_stats_reply_time
  flow_stats_reply_time = time.time() - notification_time

  sending_dpid = event.connection.dpid
  sending_address = event.connection.sock.getpeername()[0]

  bad_flows = 0
  flow_bw_list = []

  dpid = str(dpidToStr(event.dpid))

  # Get indexes of flow_list
  #print "Flow stats received from: " , dpid
  dpid_str = dpid.replace("-", "")
  #print "Sending dpid: ", sending_dpid
  
  for i in range(len(switch_states)):

    #print "switch stats dpid: ", switch_states[i]['dpid']
    remaining_bw = 100000000  

    if switch_states[i]['dpid'] == dpid_str:

      if updating == 1:

        flow_list = flow_stats_to_list(event.stats)
        #print "Raw flow list received: ", flow_list
        #print "Old flow list: ", switch_states[i]['flow_stats']

        if not flow_list:
		print "Flow list empty!"
		queues_dict = dict.fromkeys(['Response','dpid'])
                queues_dict['dpid'] = sending_dpid
                queues_dict['Response'] = "Clear"
	        response_message = json.dumps(str(queues_dict))
  
                response_socket = create_socket()
                send_message(response_socket,sending_address, response_port, response_message)
                close_connection(response_socket)
		return

        indexes_to_process = [flow_index for flow_index, flow in enumerate(flow_list) if str(flow['match']['nw_dst'])==server_target]
      
        current_flows = get_bw_flow_list(flow_list, indexes_to_process)
        #print "current flows: ", current_flows
        #new_flows_indexes = []
        stopped_flows_indexes = []
        #uptaded_indexes = []

        for j in range(len(current_flows)):
          # Flow still exists, getting bw/s
          for k in range(len(switch_states[i]['flow_stats'])):
            if (current_flows[j]['nw_src'] == switch_states[i]['flow_stats'][k]['nw_src']) and (current_flows[j]['nw_src'] == switch_states[i]['flow_stats'][k]['nw_src']) and (switch_states[i]['flow_stats'][k]['goodBehaved'] == True):
              switch_states[i]['flow_stats'][k]['reportedBw'] = current_flows[j]['reportedBw']
              #uptaded_indexes.append(k)
              break

            # If it wasn't in k-1 and k we could have a) flow ceased b) flow is a new one
          if (not any(src['nw_src'] ==  current_flows[j]['nw_src'] for src in switch_states[i]['flow_stats'])):
            # New flow does not exist in the old flow stats, append it
            #new_flows_indexes.append(j)
            switch_states[i]['flow_stats'].append(current_flows[j])
            continue

        for j in range(len(switch_states[i]['flow_stats'])):
          if (not any(src['nw_src'] ==  switch_states[i]['flow_stats'][j]['nw_src'] for src in current_flows)):
          # New flow does not exist in the old flow stats, append it
            stopped_flows_indexes.append(j)
            continue
          
        # Remove the flows that stopped from the global flow list
        removeset = set(stopped_flows_indexes)
        newlist = [v for k, v in enumerate(switch_states[i]['flow_stats']) if k not in removeset]
        del switch_states[i]['flow_stats'][:]
        for j in range(len(newlist)):
          switch_states[i]['flow_stats'].append(newlist[j])
        #for j in range(len(stopped_flows_indexes)):
        #del switch_states[i]['flow_stats'][stopped_flows_indexes[j]]
        
	#print "Giving bw to: ", switch_states[i]['flow_stats']  
        switch_states[i]['flow_stats'] = assign_bw(switch_states[i]['flow_stats'], switch_states[i]['bw_policy'])
        #print "Updating: Flow stats: " + str(switch_states[i]['flow_stats'])
      
        queues_dict = dict.fromkeys(['Response','dpid','bw_list'])
        queues_dict['dpid'] = sending_dpid
        queues_dict['Response'] = "Decrement"
	queues_dict['bw_list'] = []
        
        for j in range(len(switch_states[i]['flow_stats'])):
          bw_dict = dict.fromkeys(['nw_src', 'nw_dst', 'bw', 'action']) 
          bw_dict['nw_src'] = switch_states[i]['flow_stats'][j]['nw_src']
          bw_dict['nw_dst'] = switch_states[i]['flow_stats'][j]['nw_dst']
          bw_dict['bw'] = switch_states[i]['flow_stats'][j]['bw']
          bw_dict['action'] = switch_states[i]['flow_stats'][j]['action']
          queues_dict['bw_list'].append(bw_dict)
        
        response_message = json.dumps(str(queues_dict))

        response_socket = create_socket()
        send_message(response_socket,sending_address, response_port, response_message)
        close_connection(response_socket)

      else:

        flow_list = flow_stats_to_list(event.stats)
        indexes_to_process = [flow_index for flow_index, flow in enumerate(flow_list) if str(flow['match']['nw_dst'])==server_target]

        #print "Raw flow list: ", flow_list

        switch_states[i]['flow_stats'] = get_bw_flow_list(flow_list, indexes_to_process)
        #print "Flow stats: "  + str(switch_states[i]['flow_stats'])

        if not switch_states[i]['flow_stats']:
          return
            
        switch_states[i]['flow_stats'] = assign_bw(switch_states[i]['flow_stats'], switch_states[i]['bw_policy']) 

        queues_dict = dict.fromkeys(['Response','dpid','bw_list'])
        queues_dict['dpid'] = sending_dpid
        queues_dict['Response'] = "Decrement"
        queues_dict['bw_list'] = switch_states[i]['flow_stats']

        response_message = json.dumps(str(queues_dict))

        response_socket = create_socket()
        send_message(response_socket,sending_address, response_port, response_message)
        close_connection(response_socket)
        
      if updating == 1:
        global updating
        updating = 0
        response_message = json.dumps(str(queues_dict))

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
  fair_rate = float(capacity/num_flows)

  #print "estimated: " + str(estimated_bw,) + " num flows: " + str(num_flows)
  
  if estimated_bw > fair_rate:
    #print "Bad behaved"
    return False
  else:
    #print "good behaved"
    return True

def assign_bw_to_bad_behaved(capacity, remaining_bw, num_bad_flows, num_total_flows, flow_rate, alfa):

  """ Assigns bw to each flow """
  #return flow_rate - (1 - math.exp(-(flow_rate-(capacity/num_total_flows))))*alfa*flow_rate
  #print "Bad behaved with: " + "capacity :" + str(capacity) + " remaining bw: " + str(remaining_bw) + " bad flows: " + str(num_bad_flows)
  #print "Total flows: " + str(num_total_flows) + "flow rate : " + str(flow_rate) + "alfa: " + str(alfa)
  fair_rate = capacity/num_total_flows
  #bad_fair_rate = capacity / num_bad_flows
  bw = flow_rate - (1 - math.exp( - abs(flow_rate - fair_rate) )) * alfa * flow_rate
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

        bw_list.append(switch_states[i]['flow_stats'][j]['reportedBw'])
        if switch_states[i]['flow_stats'][j]['goodBehaved'] == False:
          bad_flow_count = bad_flow_count + 1

      if bad_flow_count >= float(num_flows*bad_flow_count_th):
        # Number of bad flows is 90% of the total flow count, switch policy
        switch_states[i]['bw_policy'] = 'Equal'
	print "Equal Policy"
      else:
	print "Penalty policy"
        switch_states[i]['bw_policy'] = 'Penalty'

      if len(bw_list) > 1:
        if any(e is None for e in bw_list):
          return
        else:
          #print "bw_list: ", bw_list
          bw_dev = st.stdev(bw_list)
          if bw_dev > min_sla:
            #print "Drop Policy: MOF "
            switch_states[i]['drop_policy'] = 'MOF'       
          else:
            #print "Drop POlicy: Random"
            switch_states[i]['drop_policy'] = 'Random'


def launch (transparent=False, hold_down=_flood_delay):
  """
  Starts an L2 learning switch.
  """
  try:
    global _flood_delay
    _flood_delay = int(str(hold_down), 10)
    assert _flood_delay >= 0
  except:
    raise RuntimeError("Expected hold-down to be a number")

  core.registerNew(flow_fence, str_to_bool(transparent))
  #core.registerNew(ConnectTest)
  core.openflow.addListenerByName("FlowStatsReceived", _handle_flowstats_received)
  Timer(check_policy_time, check_policies, recurring = True)
  print "FlowFence launched"
