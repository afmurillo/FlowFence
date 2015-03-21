

""" Module that monitors the average network interface occupation """

import subprocess
from collections import deque
import threading

import application_switch_2
import SwitchProperties
import time

class FlowMonitor:


	""" Class that monitors network interface occupation """

        def __init__(self, samples=10, period=3, interval_time=1.0, upper_limit=10*0.8, lower_limit=10*0.6):

		self.n_samples = samples
		self.period = period
		self.interval_time = interval_time
		self.switch_properties = SwitchProperties.SwitchProperties()
		self.interfaces_list = self.switch_properties.get_interfaces()
		self.complete_interface_list = []

		for i in range(len(self.interfaces_list)):
			complete_interface_dict = dict.fromkeys(['name', 'dpid', 'capacity', 'lower_limit', 'upper_limit', 'threshold', 'samples', 'use_averages', 'monitoring', 'is_congested', 'queueList'])
			complete_interface_dict['name'] = self.interfaces_list[i]['name']
			complete_interface_dict['dpid'] = self.interfaces_list[i]['dpid']
			complete_interface_dict['capacity'] = self.interfaces_list[i]['capacity']
			complete_interface_dict['lower_limit'] = lower_limit
			complete_interface_dict['upper_limit'] = upper_limit
			complete_interface_dict['threshold'] = upper_limit
			complete_interface_dict['samples'] = []
			complete_interface_dict['prevEma'] = 0
			complete_interface_dict['currentEma'] = 0
			complete_interface_dict['use_averages'] = 0
			complete_interface_dict['monitoring'] = 0
			complete_interface_dict['is_congested'] = 0
			complete_interface_dict['queueList'] = []
			self.complete_interface_list.append(complete_interface_dict)

			for i in range(len(self.complete_interface_list)):
				self.complete_interface_list[i]['use_averages'] = deque( maxlen=self.n_samples )

			#Control variables
			self.threads_id = []
			self.reset_queues()
			self.init_window()

	def reset_queues(self):
   	    """ Clears QoS queues in all interfaces """

            for i in range(len(self.complete_interface_list)):
		subprocess.check_output('ovs-ofctl del-flows ' + self.complete_interface_list[i]['name'], shell=True)
                subprocess.check_output('./clear_queues.sh ' + self.complete_interface_list[i]['name'], shell=True)

        def init_window(self):
	    """ Inits samples window """

            for j in range(len(self.complete_interface_list)):
                for i in range(self.n_samples):
			self.complete_interface_list[j]['use_averages'].append(0)

            for i in range(self.n_samples):

                #sample list of dicts, each dict has ['name']['sample']
                result = self.get_sample()
	    for j in range(len(self.complete_interface_list)):
		    last_samples = result[j]['sample']
                    self.complete_interface_list[j]['use_averages'].popleft()
		    self.complete_interface_list[j]['use_averages'].append(last_samples)
            if i == 0:
                    self.complete_interface_list[j]['prevema'] = last_samples

	    for j in range(len(self.complete_interface_list)):
		for a_bar in enumerate(self.complete_interface_list[j]['use_averages']):
	            self.complete_interface_list[j]['currentEma'] = self.ema(a_bar, self.complete_interface_list[j]['use_averages'], self.period, self.complete_interface_list[j]['prevEma'], smoothing=None)
                    self.complete_interface_list[j]['prevEma'] = self.complete_interface_list[j]['currentEma']


	def update_window(self):

		""" Updates the sample window """

		for i in range(self.n_samples):

			# Sample list of dicts, each dict has ['name']['sample']
			result = self.get_sample() # < ---- GOTTA CHECK THIS
			last_samples=0

			for j in range(len(self.complete_interface_list)):
				last_samples = result[j]['sample']
				self.complete_interface_list[j]['use_averages'].popleft()
				self.complete_interface_list[j]['use_averages'].append(last_samples)


			for j in range(len(self.complete_interface_list)):
	                        if i == 0:
        	                        self.complete_interface_list[j]['prevema'] = last_samples
				for a_bar in enumerate(self.complete_interface_list[j]['use_averages']):
					self.complete_interface_list[j]['currentEma'] = self.ema(a_bar, self.complete_interface_list[j]['use_averages'], self.period, self.complete_interface_list[j]['prevEma'], smoothing=None)
					self.complete_interface_list[j]['prevEma'] = self.complete_interface_list[j]['currentEma']

	def start_monitoring(self):
		""" Starts the thread that monitors interface occupation """

		self.report_object = application_switch_2.ApplicationSwitch()
		self.monitoring=1
		self.threads_id.append(threading.Thread(name = 'Monitor', target=self.monitor))
		self.threads_id[0].start()

	def stop_monitoring(self):

		""" Unused """
		self.monitoring=0

	#toDo: Handle
	def congestion_stopped(self):

		""" Unused """
		self.is_congested=0

	def monitor(self):

		""" Obtains a new sample of the interface occupation average, and in case of congestion, notifies the main module """

		while self.monitoring == 1:

			try:
				self.update_window()
				for j in range(len(self.complete_interface_list)):

					print "update, ema: " + str(self.complete_interface_list[j]['currentEma'])
					print "current threshold: " + str(self.complete_interface_list[j]['threshold'])
					if (self.complete_interface_list[j]['is_congested'] == 0) and (self.complete_interface_list[j]['currentEma'] >= self.complete_interface_list[j]['threshold']):
						#print "Congested"
						self.complete_interface_list[j]['threshold'] = self.complete_interface_list[j]['lower_limit']
						#print "Reporting congestion"
						self.report_object.congestion_detected(self.complete_interface_list[j])

					elif (self.complete_interface_list[j]['is_congested'] == 1) and (self.complete_interface_list[j]['currentEma'] <= self.complete_interface_list[j]['threshold']):
						self.complete_interface_list[j]['is_congested'] = 0
						self.complete_interface_list[j]['threshold'] = self.complete_interface_list[j]['upper_limit']
						#print "Congestion ceased"
						self.report_object.congestion_ceased()

			except KeyboardInterrupt:
				print " \n *** So long and thanks for all the fish! *** "
				self.monitoring = 0
				break

	def create_queues(self, controller_message):

		""" Creates the QoS queues, one queue is created for each flow """

		for i in range(len(self.complete_interface_list)):
			self.complete_interface_list[i]['queueList']=self.init_queues(self.complete_interface_list[i]['name'],controller_message['bw_list'])
			self.set_queues_bw(self.complete_interface_list[i]['queueList'])
			self.report_object.queues_ready(self.complete_interface_list[i],controller_message['bw_list'],self.complete_interface_list[i]['queueList'])
			break

        @classmethod
	def init_queues(cls, interface_name, bw_list):
		""" Inits the QoS queues """

		#print "Initing queues for: " + str(interface_name)
		queues_list=[]
		qos_string='ovs-vsctl -- set Port ' + interface_name + ' qos=@fenceqos -- --id=@fenceqos create QoS type=linux-htb other-config:max-rate=16000000 other-config:max-rate=16000000'
		queues_string=''

		# Example
		# queues:0=@queue0 queues:1=@queue1

		for j in range(len(bw_list)):
			a_queue_dict=dict.fromkeys(['queueId','queueuuid','nw_src','nw_dst','bw'])
			a_queue_dict['queueId']=j
			a_queue_dict['nw_src']=bw_list[j]['nw_src']
			a_queue_dict['nw_dst']=bw_list[j]['nw_dst']
			a_queue_dict['bw'] = bw_list[j]['bw']
			a_queue= 'queues:' + str(a_queue_dict['queueId']) +'=@queue' + str(a_queue_dict['queueId']) + ' '
			queues_string=queues_string+a_queue
			#print "Created queue dict: " + str(a_queue_dict)
			queues_list.append(a_queue_dict)

		#queues_string='queues=0=@queue0'+queues_string
		#toDo: Check the string creation

		#queues_creation='-- --id=@queue0 create Queue other-config:max-rate=16000000 '
		#toDo: Check the numqueues handling

		for j in range(len(bw_list)):
			a_creation='-- --id=@queue' + str(queues_list[j]['queueId']) + ' create Queue other-config:min-rate=16000000 other-config:max-rate=16000000 '
			queues_creation=queues_creation+a_creation

		command=qos_string + ' ' + queues_string + ' ' + queues_creation
		#print "Queue command: \n " + str(command)
		subprocess.check_output(command, shell=True)

		#print "Queues list " + str(queues_list)

		# Getting uuid of each queue
		queues_string = subprocess.check_output("ovs-vsctl list Queue", shell=True)
		#print "Queues Ready: " + str(queues_string)

		allqueues_string = subprocess.check_output("ovs-vsctl list QoS  | grep queues", shell=True)

		for j in range(len(queues_list)):
			queues_list[j]['queueuuid']=allqueues_string.split(":")[1].split(",")[j+1].split("=")[1].split('}\n')[0].strip()

		#print "Queue List: " + str(queues_list)
		return queues_list

        @classmethod
	def set_queues_bw(cls, queues_list):

		""" Sets the queue bw, according to the policy defined by the SDN controller """

		for i in range(len(queues_list)):
			subprocess.check_output("ovs-vsctl set queue " + queues_list[i]['queueuuid'] + " other-config:max-rate="+str(queues_list[i]['bw'] + "other-config:min-rate="+str(queues_list[i]['bw']), shell=True)

        @classmethod
	def get_uuid(cls):
		""" Returns the queue unique id """
		uuid=subprocess.check_output("ovs-vsctl list qos | grep queues | awk '{print $4;}'", shell=True).split('=')[1].split('}')[0]
		return uuid

        @classmethod
        def get_rate(cls,uuid):
		""" Returns the queue rate in bytes/s """
		rate=float(subprocess.check_output("ovs-vsctl list queue " + uuid + " | grep other_config | awk '{print $3;}'", shell=True).split('=')[1].split('"')[1])
		return rate

	def ema(self, a_bar, series, period, prevma, smoothing=None):
            '''Returns the Exponential Moving Average of a series.
	    Keyword arguments:
            a_bar         -- currrent index or location of the series
            series      -- series of values to be averaged
            period      -- number of values in the series to average
            prevma      -- previous exponential moving average
            smoothing   -- smoothing factor to use in the series.
                valid values: between 0 & 1.
                default: None - which then uses formula = 2.0 / (period + 1.0)
                closer to 1 to gives greater weight to recent values - less smooth
                closer to 0 gives greater weight to older values -- more smooth
            '''

            smoothing = 0.8

            if a_bar[0] <= 0:
                return series[0]
	    elif a_bar[0] < period:
		return self.cumulative_sma(a_bar[0], series, prevma)

	    return prevma + smoothing * (series[a_bar[0]] - prevma)

        @classmethod
	def cumulative_sma(cls, a_bar, series, prevma):
            """
            Returns the cumulative or unweighted simple moving average.
            Avoids averaging the entire series on each call.
	    Keyword arguments:
            a_bar     --  current index or location of the value in the series
            series  --  list or tuple of data to average
            prevma  --  previous average (n - 1) of the series.
            """
            if a_bar[0] <= 0:
		return series[0]
            else:
		return prevma + ((series[a_bar[0]] - prevma) / (a_bar[0] + 1.0))

	def get_sample(self, interval_time=1.0):

		""" Obtains a sample of the interface occupation in bytes/s """
		samples_list=[]

		for j in range(len(self.complete_interface_list)):
			sample_dict=dict.fromkeys(['interface_name'],['sample'])
			samples_list.append(sample_dict)

		#lists to Store first and second sample value of each interface
		# Each value of a and b represents a sample taken in each interface
		sample_1 = []
		sample_2 = []

		for j in range(len(self.complete_interface_list)):
			sample_1.append((float(subprocess.check_output("cat /proc/net/dev | grep " + self.complete_interface_list[j]['name'] + " | awk '{print $10;}'", shell=True).split('\n')[0])))

		time.sleep(interval_time)

		for j in range(len(self.complete_interface_list)):

			sample_2.append((float(subprocess.check_output("cat /proc/net/dev | grep " + self.complete_interface_list[j]['name'] + " | awk '{print $10;}'", shell=True).split('\n')[0])))
			samples_list[j]['name'] = self.complete_interface_list[j]['name']
			#samples_list[j]['sample']=((b[j]-a[j])/1048576) In MBytes
			samples_list[j]['sample']=sample_2[j]-sample_1[j]
		return samples_list

if __name__ == "__main__":

    SOME_SAMPLES = 10
    PERIOD = 3  #number of bars to average
    AN_INTERVAL_TIME = 1.0

    #toDo: Handle this as a percentage of total link capacity
    AN_UPPER_LIMIT = 0.4
    LOWER_LIMIT = 0.41

    USE_AVERAGES = deque( maxlen=SOME_SAMPLES )
    CODE = FlowMonitor(SOME_SAMPLES, AN_INTERVAL_TIME, AN_UPPER_LIMIT)
    CODE.start_monitoring()
