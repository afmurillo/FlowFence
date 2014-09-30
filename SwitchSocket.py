import socket
import sys
from time import *
import json
from threading import Thread
#from ApplicationSwitch import ApplicationSwitch
import subprocess

class SwitchSocket(Thread):

	def __init__(self, applicationPort):
		Thread.__init__(self)
		self.applicationPort = applicationPort
#		self.reportObject

	def run(self):
		self.sock = socket.socket()     # Create a socket object
		host = subprocess.check_output("ifconfig | grep 10.1.4 | awk '{print $2;}'", shell=True).split(':')[1].split('\n')[0]
		self.sock.bind((host, self.applicationPort))        				# Bind to the port
		self.sock.listen(5)

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

class handle_message(Thread):

	def __init__(self,received,connections, addr):
		Thread.__init__(self)
		self.received = received
		self.myconnections = connections
		self.srcAddress = addr[0]
		#self.responsePort=23456
		#self.bwForNewFlows=0.1
		#self.reportObject = ApplicationSwitch()
		print self.myconnections

	def run(self):
		self.reportObject.messageFromController(self.received,self.myconnections,self.srcAddress)
