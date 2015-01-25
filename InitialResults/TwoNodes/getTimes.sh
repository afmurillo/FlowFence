for i in `ls | grep ping`; do 

 	echo $i
	rm $i/times.txt
	for j in `ls $i | grep ping`; do

		echo $j
		cat $i/$j | grep from | awk '{print $7;}' | awk -F "=" '{print $2;}' >> $i/times.txt

	done

done

