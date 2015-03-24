#!/bin/bash

# Queues and qos must be explicitly deleted, this script performs that.
# WARNING! The flows associated to the qos bridge are also deletted!!!
set -e

ovs-vsctl -- clear Port eth0br QoS
ovs-vsctl -- clear Port eth1br QoS

ovs-vsctl -- --all destroy QoS
ovs-vsctl -- --all destroy Queue


