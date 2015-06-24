""" Module that handles client socket to report congestions and receive commands """

import socket
import select

class FeedbackMessage:
		"""
		Class that sends link congestion update messages to the FlowFence application run on the controller
		"""

		def __init__(self, controller_ip='127.0.0.1', application_port=12345):

			self.dst_ip = controller_ip
			self.app_port = application_port


		def send_message(self,message, an_ip, a_port):
			""" Sends a message to the controller """

			self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			self.socket.connect((an_ip, a_port))

			try:
				ready_to_read, ready_to_write, in_error = select.select([self.socket,], [self.socket,], [], 5)
			except select.error:
				#self.socket.shutdown(2)
				#self.close_connection()	
				print "Error with receiving socket"
				return
			except: 
				#self.socket.shutdown(2)
				#self.close_connection()
				print "Socket error"
				return
			if len(ready_to_write) > 0:

				self.socket.send(message)
				self.close_connection()

		def close_connection(self):
			""" Closes the connection with the SDN controller """
			self.socket.close()
