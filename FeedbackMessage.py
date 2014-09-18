from socket import *
import sys
from time import *
import json
from Crypto.Cipher import AES

class FeedbackMessage:
		"""
		Class that sends link congestion update messages to the FlowFence application run on the controller
		"""

		def __init__(self, version = 1, priority = 0, controllerIp='127.0.0.1', applicationPort=12345):

			self.version=version			
			self.piority=priority
			self.dstIp=controllerIp
			self.appPort = applicationPort

			print controllerIp
			print applicationPort

			self.socket = socket(AF_INET, SOCK_STREAM)			
	
		def createMAC(self, key, message):

			hasher = AES.new(key, AES.MODE_CBC, 'This is an IV456')
			keySize=16

			if (len(message) % keySize) != 0:
				#Should do stuffing
				base=int(len(message)/ 16)
				diff=16*(base+1)-len(message)
				
				stuff=''
				stuff=stuff.zfill(diff)

				message=message+stuff

			ciphertext = hasher.encrypt(message)
			MAC=str(ciphertext[len(ciphertext)-4:])

			return MAC

		def updateTimeStamp(self):
			return int(time())

		def createCommonHeader( self, version=1, aType='request', proto='udp', priority=0, flags='none'):

			return [{'version':version, 'type':aType, 'proto':proto, 'priority':priority, 'flags':flags, 'timeStamp':self.updateTimeStamp() }]

		def createNopFeedback( self, key,version=1, aType='request', proto='udp', priority=0, flags='none', linkId='127.0.0.1'):

			#Gets common header
			commonObj=self.createCommonHeader(version,aType, proto, priority, flags)

			#todo: Update
			ipSrc=inet_aton('127.0.0.1')

			tsStr=str(commonObj[0]['timeStamp'])
			ts=tsStr[len(tsStr)-4:]

			linkNull='NN'
			nop='np'

			MAC = self.createMAC(key, ipSrc + linkId + ts + linkNull + nop)

			return [ {'common':commonObj ,'linkId':linkId,'mac':MAC}]    


		def createIncrFeedback( self, key, src, version=1, aType='request', proto='udp', priority=0, flags='none', dst='127.0.0.1', linkId='aa'):
			commonObj=self.createCommonHeader(version,aType, proto, priority, flags)

			#todo: Update
			ipSrc=src			
			print 'Dpid: ' + str(ipSrc)
			tsStr=str(commonObj[0]['timeStamp'])
			ts=tsStr[len(tsStr)-4:]
			mode='y'
			mon='u'
				
			MAC = self.createMAC(key, str(ipSrc) + dst + ts + linkId + mode + mon)	

			nopToken=self.createNopFeedback(key,version, aType, proto, priority, flags, dst)

			return [ {'common':commonObj ,'src':ipSrc,  'linkId':linkId, 'order':mon, 'mac':MAC, 'nop':nopToken } ]
			 

		def createDecrFeedback(self, key, sharedKey, src, version=1, aType='request', proto='udp', priority=0, flags='none', dst='127.0.0.1', linkId='aa' ):

			commonObj=self.createCommonHeader(version,aType, proto, priority, flags)
			nopToken=self.createNopFeedback(key,version, aType, proto, priority, flags, dst)

			ipSrc=src		
			print 'Dpid: ' + str(ipSrc)	
			tsStr=str(commonObj[0]['timeStamp'])
			ts=tsStr[len(tsStr)-4:]
			mode='y'
			mon='d'	

			MAC = self.createMAC(key, str(ipSrc) + dst + ts + linkId + mode + mon + nopToken[0]['mac'])	
			#MAC='a'
			return [ {'common':commonObj , 'src':ipSrc, 'linkId':linkId, 'order':mon, 'mac':MAC } ]

		def sendMessage(self,message, ip, port):
			
			#print 'socket sending message'

			#toDo: Is this the better way? we try a connect each time, for TCP timeouts
			self.socket = socket(AF_INET, SOCK_STREAM)
			self.socket.connect((ip, port))
			self.socket.send(message)	

			#print 'socket sent message'

		def closeConnection(self):				
			self.socket.close()

if __name__=="__main__":

	#def create

	feedback = FeedbackMessage()

	#Check where the key should be stored :\
	Ka='\x08+\xe1\x8d\x85\x86E\x02?H.K\xf7@\xe5\xeb'
	Kab='\x17\xf4\x9c\x98\xd6\x84\xcb\xcf\xe6\x93\x11\xe2\xbaI\xdfM'

	# Created with
	#from Crypto import Random
	#rndfil = Random.new()
	#Ka=rndfile.read(16)

	#Parameters for the creation of MAC
	aVersion=1
	aType='request'
	aProto='udp'
	aPriority=0
	someFlags='none'

	dstIp='127.0.0.1'

	anId=inet_aton(dstIp)


	#nopMessage=createNopFeedback(Ka,aVersion, aType, aProto, aPriority, someFlags, anId)
	#print "Nop message"
	#print nopMessage
	#feedbackMsg = json.dumps(str(nopMessage))
	#print feedbackMsg


	#increaseMsg = createIncrFeedback(Ka,aVersion, aType, aProto, aPriority, someFlags, anId)
	#print "Incr message"
	#print increaseMsg
	#feedbackMsg = json.dumps(str(increaseMsg))
	#print feedbackMsg

	decrMsg = createDecrFeedback(Ka, Kab, aVersion, aType, aProto, aPriority, someFlags, anId)
	feedbackMsg = json.dumps(str(decrMsg))

	print feedbackMsg

	s = socket(AF_INET, SOCK_STREAM)
	host=dstIp #itanhanga
	s.connect((dstIp, 12345))
	s.send(feedbackMsg) #msg sent
	s.close()


	#For reception use:
	#encoded_data = json.loads(json_encoded)
	#dictData=eval(encoded_data)
