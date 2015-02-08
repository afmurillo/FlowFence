echo "Running"
for i in `ls | grep http`; do 

 	echo $i
	rm $i/times.txt
	for j in `ls $i | grep httP`; do

		echo $j
		cat $i/$j | grep Reply | grep time | awk '{print $5;}' >> $i/times.txt

	done

done

