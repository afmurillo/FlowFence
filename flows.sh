#!/bin/bash
flowsString=`ovs-ofctl dump-flows eth1br | grep cookie`
numFlows=`echo $flowsString | wc -l`
dl_src=`echo $flowsString |grep -o 'dl_src=[^ ,]\+' | awk 'BEGIN { FS = "=" } ; {print $2}'`
dl_dst=`echo $flowsString |grep -o 'dl_dst=[^ ,]\+' | awk 'BEGIN { FS = "=" } ; {print $2}'`
nw_src=`echo $flowsString |grep -o 'nw_src=[^ ,]\+' | awk 'BEGIN { FS = "=" } ; {print $2}'`
nw_dst=`echo $flowsString |grep -o 'nw_dst=[^ ,]\+' | awk 'BEGIN { FS = "=" } ; {print $2}'`

n_bytes=`echo $flowsString |grep -o 'n_bytes=[^ ,]\+' | awk 'BEGIN { FS = "=" } ; {print $2}'`
action=`echo $flowsString |grep -o 'actions=[^ ,]\+' | awk 'BEGIN { FS = "=" } ; {print $2}'`

#echo Original flow String $flowsString
echo NumFlows=$numFlows
echo dl_srcs=$dl_src
echo dl_Dst=$dl_dst
echo nw_src=$nw_src
echo nw_dst=$nw_dst
echo n_bytes=$n_bytes
echo action=$action