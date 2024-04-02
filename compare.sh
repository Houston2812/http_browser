#!/bin/bash

RED='\033[0;31m'
NC='\033[0m'
GREEN='\033[0;32m'

folder=$1

echo Target folder: $folder

for filename in ./$folder/*; do

	file=$(echo $filename | grep -o -E  "([A-Za-z0-9_()]+).([A-Za-z]+)$") 
	
	cmp ./proj/$file ./$folder/$file 

	status=$?

	if [[ $status = 0 ]]; then
		echo -e "[+] $file received ${GREEN}correctly${NC}"
	else
		echo -e "[-] $file received ${RED}incorrectly${NC}"
	fi
	
done
	

