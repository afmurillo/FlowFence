#!/bin/bash

# Queues and qos must be explicitly deleted, this script performs that.
# WARNING! The flows associated to the qos bridge are also deletted!!!
set -e

#ovs-vsctl clear port $1 qos
#ovs-vsctl -- --all destroy Queue
#ovs-vsctl -- --all destroy QoS

ovs-vsctl -- clear Port eth0br QoS
ovs-vsctl -- clear POrt eth1br QoS

#ovs-vsctl -- --if-exists destroy QoS eth0br
#ovs-vsctl -- --if-exists destroy QoS eth1br

ovs-vsctl -- --all destroy QoS

ovs-vsctl -- --all destroy Queue


