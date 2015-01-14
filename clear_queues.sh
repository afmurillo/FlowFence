#!/bin/bash

# Queues and qos must be explicitly deleted, this script performs that.
# WARNING! The flows associated to the qos bridge are also deletted!!!
set -e

ovs-vsctl clear qos $1 queues
ovs-vsctl -- --all destroy Queue
ovs-vsctl -- --all destroy QoS

