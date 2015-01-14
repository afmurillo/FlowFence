for i in `ovs-vsctl list qos | grep _uuid | awk '{print $3;}'`
	ovs-vsctl destroy qos $i;
done
