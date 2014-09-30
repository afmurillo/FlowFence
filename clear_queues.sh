#!/bin/bash

# Queues and qos must be explicitly deleted, this script performs that.
# WARNING! The flows associated to the qos bridge are also deletted!!!
ovs-vsctl clear port $1 qos

qosid=$(ovs-vsctl list qos | grep _uuid |  awk '{print $3;}')
queueid=$(ovs-vsctl list queue | grep _uuid |  awk '{print $3;}')

ovs-vsctl destroy qos $qosid
ovs-vsctl destroy queue $queueid

