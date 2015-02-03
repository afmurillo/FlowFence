echo "Running"
for i in `ls | grep http`; do 

 	echo $i
	rm $i/nwk.txt
	for j in `ls $i | grep httP`; do

		echo $j
		cat $i/$j  | grep Net | awk '{print $3;}' >> $i/nwk.txt


	done

done

