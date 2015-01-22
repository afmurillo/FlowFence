import os
import subprocess

class SwitchProperties:

        def getInterfaces(self):
		interfacesList=[]
                interfacesName=[]

                #interfacesString=subprocess.check_output("ovs-vsctl show | grep Bridge | awk '{print $2;}'",shell=True).split("\n")
                interfacesString=subprocess.check_output("ovs-vsctl show | grep Bridge  | grep eth0br | awk '{print $2;}'",shell=True).split("\n") 

                print "interfaces List: " + str(interfacesString)
                for i in range(len(interfacesString)):
                        if not interfacesString[i]:
                                continue
                        else:
                                interfacesName.append(interfacesString[i])
                                interfaceDict = dict.fromkeys(['name','dpid','capacity'])
                                interfaceDict['name']=interfacesString[i]
                                interfaceDict['dpid']=self.getDpid(interfaceDict['name'])
                                interfaceDict['capacity']=self.getInterfaceCapacity(interfaceDict['name'])
                                interfacesList.append(interfaceDict)

                return interfacesList

        def getDpid(self, interfaceName):
        		awk="{print $3;}'"
        		awkString="awk '" + awk
        		return subprocess.check_output('ovs-vsctl list bridge ' + interfaceName + ' | grep datapath_id | ' + awkString, shell=True).split("\n")[0]

        def getInterfaceCapacity(self, interfaceName):

                #todo: Is there a way of finding a vif capacity? Already used: lshw, ethtool, dmesg, miitool
                #Capacity is returned in bytes!!!!
                return 100000000

if __name__=="__main__":

        aSwitch = SwitchProperties()
        aSwitch.getInterfaces()

