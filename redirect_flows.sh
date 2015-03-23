ovs-ofctl add-flow eth0br dl_type=0x800,nw_src=10.1.1.1,nw_dst=10.1.2.1,actions=set_queue:0,normal
ovs-ofctl add-flow eth0br dl_type=0x800,nw_src=10.1.1.3,nw_dst=10.1.2.1,actions=set_queue:1,normal
