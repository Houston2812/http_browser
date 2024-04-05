# HTTP Browser
By: Huseyn Gambarov

# Client-side
On the client side, _client.py_ is able to request files from the server by sending GET requests. The obtaine files are stored under the "/proj" directory.

This client implements both pipelining and multiple requests features of HTTP 1.1.

Additionally, there is a _compare.sh_ script that is able to compare response that is stored under "/proj" directory to the expected response. 

# Execution
1. Create python virtual environment:
    * _python3 -m venv venv_
    * _source ./venv/bin/activate_
2. Install dependencies:
    * _pip install -r requirements.txt_

### Run client:  
* _python3 client.py IP_
* _python3 client.py IP:PORT_

Both variations will work. When port is not specified it is set to 80 by default.

### Run checker:  
* _./compare.sh path_to_folder_with_expected_results_

The checker script compares files in the expected folder to the files in proj folder using **cmp** utility. 

# Technical specifications:
1. Uses n-ary tree to parse dependencies and create dependency tree.
2. Assign request to each socket using Round Robin mechanism to handle "Multiple Requests feature" of HTTP 1.1
3. During load balancing the nodes are selected using the postorder traversal of the tree. 

# Used dependencies
* colorama==0.4.6
* bitstring==4.1.4
* colorama==0.4.6

# System versions
* Python 3.11.6
* Linux 6.5.0-21-generic x86_64
* "Ubuntu 23.10"

