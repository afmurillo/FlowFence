""" Module that handles client socket to report congestions and receive commands """

import socket

class FeedbackMessage:
		"""
		Class that sends link congestion update messages to the FlowFence application run on the controller
		"""

		def __init__(self, version=1, priority=0, controller_ip='127.0.0.1', application_port=12345):

			self.version = version
                        self.piority = priority
			self.dst_ip = controller_ip
			self.app_port = application_port

			print controller_ip
			print application_port

			self.socket = socket.socket(AF_INET, SOCK_STREAM)

		def send_message(self,message, an_ip, port):
			""" Sends a message to the controller """

			self.socket.connect((an_ip, port))
			self.socket.send(message)

		def close_connection(self):
			""" Closes the connection with the SDN controller """
			self.socket.close()
