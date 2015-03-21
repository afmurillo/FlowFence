root@pdc-1:~/FlowFenceGit/FlowFence# ovs-ofctl dump-flows eth0br
NXST_FLOW reply (xid=0x4):
 cookie=0x0, duration=1.360s, table=0, n_packets=2, n_bytes=1180, idle_timeout=5, hard_timeout=5, idle_age=0, priority=65535,icmp,in_port=1,vlan_tci=0x0000,dl_src=00:b5:73:9f:7b:d1,dl_dst=00:b6:78:9f:7b:d2,nw_src=10.1.2.1,nw_dst=10.1.1.1,nw_tos=192,icmp_type=3,icmp_code=3 actions=LOCAL
 cookie=0x0, duration=3.230s, table=0, n_packets=35, n_bytes=3290, idle_timeout=5, hard_timeout=5, idle_age=0, priority=65535,tcp,in_port=1,vlan_tci=0x0000,dl_src=00:b5:73:9f:7b:d1,dl_dst=00:b6:78:9f:7b:d2,nw_src=10.1.2.1,nw_dst=10.1.1.3,nw_tos=0,tp_src=5001,tp_dst=56910 actions=LOCAL
 cookie=0x0, duration=19.796s, table=0, n_packets=183, n_bytes=292990, idle_age=0, priority=65535,ip,nw_src=10.1.1.3,nw_dst=10.1.2.1 actions=enqueue:1:1
 cookie=0x0, duration=19.792s, table=0, n_packets=38617, n_bytes=36827430, idle_age=0, priority=65535,ip,nw_src=10.1.1.1,nw_dst=10.1.2.1 actions=enqueue:1:2
root@pdc-1:~/FlowFenceGit/FlowFence# ovs-vsctl list QoS
_uuid               : 2b652677-ab99-4ea6-97b7-530821c6d6ee
external_ids        : {}
other_config        : {max-rate="16000000"}
queues              : {0=dc83d1dd-d2fd-4fa6-a2e9-4161b51530c1, 1=5c1e592f-5bc1-42c3-9196-dd0622db2be2, 2=d07cbdba-b6b9-4a1f-9218-d30e812c956d}
type                : linux-htb

root@pdc-1:~/FlowFenceGit/FlowFence# ovs-vsctl list Queue
_uuid               : dc83d1dd-d2fd-4fa6-a2e9-4161b51530c1
dscp                : []
external_ids        : {}
other_config        : {max-rate="16000000"}

_uuid               : d07cbdba-b6b9-4a1f-9218-d30e812c956d
dscp                : []
external_ids        : {}
other_config        : {max-rate="0.0", min-rate="0.0"}

_uuid               : 5c1e592f-5bc1-42c3-9196-dd0622db2be2
dscp                : []
external_ids        : {}
other_config        : {max-rate="16000000.0", min-rate="16000000.0"}
root@pdc-1:~/FlowFenceGit/FlowFence# ovs-ofctl dump-flows eth0br
NXST_FLOW reply (xid=0x4):
 cookie=0x0, duration=1.108s, table=0, n_packets=2, n_bytes=1180, idle_timeout=5, hard_timeout=5, idle_age=0, priority=65535,icmp,in_port=1,vlan_tci=0x0000,dl_src=00:b5:73:9f:7b:d1,dl_dst=00:b6:78:9f:7b:d2,nw_src=10.1.2.1,nw_dst=10.1.1.1,nw_tos=192,icmp_type=3,icmp_code=3 actions=LOCAL
 cookie=0x0, duration=4.937s, table=0, n_packets=48, n_bytes=4512, idle_timeout=5, hard_timeout=5, idle_age=0, priority=65535,tcp,in_port=1,vlan_tci=0x0000,dl_src=00:b5:73:9f:7b:d1,dl_dst=00:b6:78:9f:7b:d2,nw_src=10.1.2.1,nw_dst=10.1.1.3,nw_tos=0,tp_src=5001,tp_dst=56910 actions=LOCAL
 cookie=0x0, duration=37.546s, table=0, n_packets=341, n_bytes=572746, idle_age=0, priority=65535,ip,nw_src=10.1.1.3,nw_dst=10.1.2.1 actions=enqueue:1:1
 cookie=0x0, duration=37.542s, table=0, n_packets=74320, n_bytes=70898177, idle_age=0, priority=65535,ip,nw_src=10.1.1.1,nw_dst=10.1.2.1 actions=enqueue:1:2




 ovs-vsctl -- set Port "eth0br" qos=@fenceqos -- --id=@fenceqos create QoS type=linux-htb other-config:max-rate=16000000 other-config:max-rate=16000000
 queues=0=@queue0,1=@queue1,2=@queue2 
 -- --id=@queue0 create Queue other-config:max-rate=16000000 -- --id=@queue1 create Queue other-config:min-rate=16000000 other-config:max-rate=16000000 -- --id=@queue2 create Queue other-config:min-rate=16000000 other-config:max-rate=16000000 

 ovs-vsctl -- set Port "eth0br" qos=@fenceqos -- --id=@fenceqos create QoS type=linux-htb other-config:max-rate=16000000 other-config:max-rate=16000000
 queues=0=@queue0,1=@queue1
 -- --id=@queue0 create Queue other-config:max-rate=16000000 -- --id=@queue1 create Queue other-config:min-rate=16000000 other-config:max-rate=16000000 -- --id=@queue2 create Queue other-config:min-rate=16000000 other-config:max-rate=16000000 


Queues message sent: [{'reportedBw': 6276196368, 'nw_dst': '10.1.2.1/32', 'bw': 16000000.0, 'action': 1, 'goodBehaved': True, 'nw_src': '10.1.1.3'}, {'reportedBw': 37121496, 'nw_dst': '10.1.2.1/32', 'bw': 0.0, 'action': 1, 'goodBehaved': False, 'nw_src': '10.1.1.1'}]

