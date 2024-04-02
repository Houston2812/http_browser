#!/bin/bash


for filename in ./expected/*; do

	file=$(echo $filename | grep -o -E  "([A-Za-z0-9()]+).([A-Za-z]+)$") 
	
	cmp ./proj/$file ./expected/$file 

	status=$?

	if [[ $status = 0 ]]; then
		echo "$file received correctly"
	else
		echo "$file received incorrectly"
	fi

	
	#echo $data
	
done
	

