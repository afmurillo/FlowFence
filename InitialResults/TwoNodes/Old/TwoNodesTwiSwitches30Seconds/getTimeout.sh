echo "Running"
for i in `ls | grep http`; do 

 	echo $i
	rm $i/outs.txt
	for j in `ls $i | grep httP`; do

		echo $j
		cat $i/$j | grep timo | awk '{print $5;}' >> $i/outs.txt


	done

done
