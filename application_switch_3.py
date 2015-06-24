""" Main Switch module, monitors interface bandwidth usage and applies the QoS policies specified by the SDN Controller """

import FeedbackMessage
import FlowMonitor_2
import SwitchProperties

import json
import subprocess

import socket
from threading import Timer
from threading import Thread
from threading import Lock

class SwitchSocket(Thread):

	""" Class that listens for SDN controller messages  """
        def __init__(self, report_object, application_port):
                Thread.__init__(self)
                self.application_port = application_port
		self.report_object = report_object
                self.sock = socket.socket()     # Create a socket object

        def run(self):
                host = subprocess.check_output("ifconfig | grep 10.1.4 | awk '{print $2;}'", shell=True).split(':')[1].split('\n')[0]
		print "Binding to " + str(host) + "in port " + str(self.application_port)
                self.sock.bind((host, self.application_port))                                    # Bind to the port
                self.sock.listen(5)

                while True:
                        try:
                                client, addr = self.sock.accept()                               # Establish connection with client
                                data = client.recv(4096)                                                # Get data from the client
                                #print 'Message from', addr                                              # Print a message confirming
                                data_treatment = HandleMessage(self.report_object, data, addr)    # Call the thread to work with the data received
                                data_treatment.setDaemon(True)                                  # Set the thread as a demond
                                data_treatment.start()                                                  # Start the thread
                        except KeyboardInterrupt:
                                print "\nCtrl+C was hitten, stopping server"
                                client.close()
                                break


class HandleMessage(Thread):

	""" Class that process the message and calls appropiate handling method """
        def __init__(self, report_object, received, addr):
                Thread.__init__(self)
                self.received = received
                self.src_address = addr[0]
                self.response_port = 23456
                self.bw_for_new_flows = 0.1
		self.report_object = report_object

        def run(self):
                self.report_object.message_from_controller(self.received)

class ApplicationSwitch:

		"""		Main class that runs in OpenFlow switches for FlowFence """

		def __init__(self):

                        #Controller message parameters
                        self.controller_ip = '10.1.4.1'

                        #todo: Handle this!
                        self.flowfence_port = 12345

                        #Link monitoring parameters
                        self.control_in_process = 0

                        self.samples = 10
                        self.period = 3
                        self.interval_time = 1.0
                        self.upper_limit = 100
                        self.lower_limit = 50

                        self.complete_flow_list = []

                        self.switch_properties = SwitchProperties.SwitchProperties()
                        self.interfaces_list = self.switch_properties.get_interfaces()

                        self.application_port = 23456

                        # toDo: change for the formula:
                        # min(((Interface Capacity)/(Minimum Bandwidth SLA));(Maximum SO queue number))
                        self.max_queue_limit = 100

                        #print self.interfaces_list

                        for i in range(len(self.interfaces_list)):
                                flow_int_dict = dict.fromkeys(['interfaceName', 'dpid'])
                                flow_int_dict['interfaceName'] = self.interfaces_list[i]['name']
                                flow_int_dict['dpid'] = self.interfaces_list[i]['dpid']
                                self.complete_flow_list.append(flow_int_dict)

                        self.msg_sender = FeedbackMessage.FeedbackMessage(self.controller_ip, self.flowfence_port)

		def congestion_detected(self, interface_dict):

			""" This method prepares and sends the congestion notification message to the controller """
			#Control variable to avoid sending multiple process
			if self.control_in_process == 0:
				#print "Interface Dict: " + str(interface_dict)
				feedback_dict = dict.fromkeys(['Notification', 'Interface'])

				feedback_dict['Notification'] = "Congestion"
				feedback_dict['Interface'] = dict.fromkeys(['capacity', 'dpid', 'name'])
				feedback_dict['Interface']['capacity'] = interface_dict['capacity']
				feedback_dict['Interface']['dpid'] = interface_dict['dpid']
				feedback_dict['Interface']['name'] = interface_dict['name']
				notification_message = json.dumps(str(feedback_dict))
				#print 'Message sent: ' + notification_message
				self.msg_sender.send_message(notification_message, self.controller_ip, self.flowfence_port)
				#self.msg_sender.close_connection()

				self.control_in_process = 1

		def congestion_ceased(self):

			""" Unused for now """
			if self.control_in_process == 1:
				#print "Congestion ceased"
				self.control_in_process = 1

		def queues_ready(self, interface_dict, bw_list, queue_list):

			""" After receiving the order to create a queue for each flo, notifies the controller that the queues are ready """
			#print "Interface Dict: " + str(interface_dict)

                        feedback_dict = dict.fromkeys(['Notification', 'queue_list', 'Interface', 'bw_list'])
                        feedback_dict['Notification'] = "QueuesDone"
                        feedback_dict['queue_list'] = queue_list
                        feedback_dict['Interface'] = dict.fromkeys(['capacity', 'dpid'])
                        feedback_dict['Interface']['capacity'] = interface_dict['capacity']
                        feedback_dict['Interface']['dpid'] = interface_dict['dpid']
                        feedback_dict['Interface']['name'] = interface_dict['name']
                        feedback_dict['bw_list'] = bw_list

                        notification_message = json.dumps(str(feedback_dict))

			print 'Queues message sent: ' + str(feedback_dict['bw_list'])
			print "Message sent to: " + str(self.controller_ip,) + " Port: " + str(self.flowfence_port)
			lock = Lock()
			lock.acquire()
			try:
				self.msg_sender.send_message(notification_message, self.controller_ip, self.flowfence_port)
        	                #self.msg_sender.close_connection()
			finally:
				lock.release()


		def message_from_controller(self, message):

			""" Handles the message from the controller, this orders the switch to create 1 queue by each flow """
			#print "Raw message received: " + str(message)
			message_dict = eval(json.loads(message))

			#print "Message Received: " + str(message_dict)
                        # En caso que el mensaje sea una indicacion de congestion, debemos preparar las filas y reportar que han sido inicializadas exitosamente
                        # Luego recibiremos un flowmod enviando los flujos a las filas respectivas
                        if message_dict['Response'] == "Decrement":
				self.link_state.create_queues(message_dict)

		@classmethod
		def get_instance(cls):

			""" Returns an instance of application switch """
			return ApplicationSwitch()


if __name__ == "__main__":

	CODE = ApplicationSwitch()

        CODE.listen_socket = SwitchSocket(CODE, CODE.application_port)
        CODE.link_state = FlowMonitor_2.FlowMonitor_2(CODE.samples, CODE.interval_time, CODE.upper_limit, CODE.lower_limit)
        print "Init Finished"

        CODE.listen_socket.setDaemon(True)
        CODE.listen_socket.start()

	CODE.link_state.start_monitoring()
