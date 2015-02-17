
""" Module that obtains network interface characteristics """

import subprocess

class SwitchProperties:

	""" Main class that obtains network interface characteristics """

        def get_interfaces(self):

		""" Obtain information about all network interfaces """

		interfaces_list = []
                interfaces_name = []

                interfaces_string = subprocess.check_output("ovs-vsctl show | grep Bridge  | grep eth0br | awk '{print $2;}'", shell=True).split("\n")

		print "interfaces List: " + str(interfaces_string)
                for i in range(len(interfaces_string)):
                        if not interfaces_string[i]:
                                continue
                        else:
                                interfaces_name.append(interfaces_string[i])
                                interface_dict = dict.fromkeys(['name', 'dpid', 'capacity'])
                                interface_dict['name'] = interfaces_string[i]
                                interface_dict['dpid'] = self.get_dpid(interface_dict['name'])
                                interface_dict['capacity'] = self.get_interface_capacity()
                                interfaces_list.append(interface_dict)

                return interfaces_list

	@classmethod
        def get_dpid(cls, interface_name):
		""" Obtains the openvswitch switch id (datapath id) """

		awk = "{print $3;}'"
		awk_string = "awk '" + awk
        	return subprocess.check_output('ovs-vsctl list bridge ' + interface_name + ' | grep datapath_id | ' + awk_string, shell=True).split("\n")[0]
	@classmethod
        def get_interface_capacity(cls):

		""" Returns the interface capacity in bytes/s """
		return 100000000

if __name__ == "__main__":

        A_SWITCH = SwitchProperties()
        A_SWITCH.get_interfaces()

