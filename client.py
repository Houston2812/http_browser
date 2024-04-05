import re
import os
import sys
import time
import math
import socket
import select
import shutil
import argparse
import binascii
from colorama import Fore
from colorama import Style
from colorama import init as colorama_init

BUF_SIZE = 4096
colorama_init()

class Logger:
    '''
        Logger class that is used as logging utility.
    '''
    def __init__(self) -> None:
        self.colors = {
            'debug': Fore.BLUE,
            'info': Fore.GREEN,
            'warning': Fore.YELLOW,
            'error': Fore.RED,
            'message': Fore.BLACK
        }

        self.signs = {
            'debug' : '[-]',
            'info': '[+]',
            'warning' : '[!]',
            'error': '[!!]',
            'message': '[...]'
        }

    def info(self, msg=''):
        level = 'info'
        print(f"{self.colors[level]}client.py - {level.upper()} - {self.signs[level]} {msg}{Style.RESET_ALL}")

    def debug(self, msg=''):
        level= 'debug'
        print(f"{self.colors[level]}client.py - {level.upper()} - {self.signs[level]} {msg}{Style.RESET_ALL}")
        # pass

    def warning(self, msg=''):
        level = 'warning'
        print(f"{self.colors[level]}client.py - {level.upper()} - {self.signs[level]} {msg}{Style.RESET_ALL}")

    def error(self, msg=''):
        level = 'error'
        print(f"{self.colors[level]}client.py - {level.upper()} - {self.signs[level]} {msg}{Style.RESET_ALL}")


class Node: 
    '''
        Node of the n-ary tree used for dependency tree.
    '''
    def __init__(self,value = None): 
        self.value=value 
        self.children=[]

    def create(self, dependencies): 
        '''
            Function to create the dependency tree with provided array of dependencies.
        '''
        for dependency in dependencies:    
            first_element, second_element = dependency.split(',')
            
            if second_element == '':
                self.value = first_element
            else:
                node = self.find(second_element)
            
                if node:
                    node.children.append(Node(first_element))
                else:
                    logger.error(f"Non existent node: {second_element}")
   
    def find(self, value):
        '''
            Function to find the node with the searched value in the tree.
        '''
        if self.value == value:
            return self

        for child in self.children:
            node = child.find( value)

            if node:
                return node

    def postorder(self):
        '''
            Generator that iterates over the rtee using the "posteroder" approach.
            It yield each element as it traverses.
        '''
        yield self

        if len(self.children) != 0:
            for child in self.children:
                yield from child.postorder()
    
    def length(self, root):  
        '''
            Function to get number of nodes in the tree.
        ''' 
        if len(root.children) == 0:
            return 1
    
        sum = 0
        for child in root.children:
            sum += self.length(child)
       
        return 1 + sum

class Requests:
    '''
        Class to handle all outgoing requests:
            * scheduling of requests per socket.
            * scheduling of expected response files per socket.
    '''
    def __init__(self) -> None:
        self.requests = {}
        self.queue = {}

    def add_request(self, fd, request, resource):
        '''
            Function to:
                1. Add request to the scheduled requests for the socket.
                2. Add expected file to the queue of expected responses.
        '''

        if fd not in self.requests.keys():
            self.requests[fd] = []

        if fd not in self.queue.keys():
            self.queue[fd] = []

        self.requests[fd].append(request)
        self.queue[fd].append(resource)

    def get_request(self, fd):
        '''
            Generator to yield requests that belong to the provided socket.
        '''
        logger.info(f"Incomind fd: {fd}")
        if fd in self.requests.keys():
            logger.debug(f"Requets for {fd}: {self.requests[fd]}")
            for index, request in enumerate(self.requests[fd]):
                yield index, request
        
    def set_request(self, fd, index, request):
        '''
            Function to update the value of scheduled request, in case if it wasnt fully sent.
        '''
        self.requests[fd][index] = request

    def clear(self, fd):
        '''
            Function to clear the list of scheduled requests per socket.
            It deletes only requests that are already fully sent.
        '''
        requests = set(self.requests[fd])

        requests.discard(b'')
        self.requests[fd] = list(requests)

    def get_queue(self, fd):
        '''
            Get list of expected files for the socket.
        '''
        return self.queue[fd]
    
    def set_queue(self, fd, queue):
        '''
            Update list of expected files for the socket.
        '''
        self.queue[fd] = queue
    
    def pop(self, fd, indices):
        '''
            Delete excepted files that were received from the queue. 
        '''
        logger.debug(f"Indices to delete: {indices}")
        while indices:
            del self.queue[fd][0]
            indices -= 1

    def is_finished(self, fd):
        '''
            Check if all scheduled requests were sent. 
        '''
        if len(self.requests[fd]) == 0:
            return True
        else:
            return False

# initialize logger as global variable
logger = Logger()

def round_robin(dependency_root, socket_num, host, port):
    '''
        Function to schedule requests per each socket.

        Parameters:
            @dependency_root  - root of the dependency tree
            @socket_num       - number of sockets that will be created
            @host             - host of the target
            @port             - port of the target
        
        Output:
            connections - dictoonary of the sockets - file_descriptor : socket
            requests    - cllass to store the list of all outgoing requests with assigned sockets
    '''

    # initialize Requests class that will store the outgoing requests
    requests = Requests()
    connections = {}

    logger.debug(f"Socket number: {socket_num}")
    
    # create socket_num sockets
    for _ in range(socket_num):
        try: 
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
        except socket.error as err: 
            logger.error("socket creation failed with error %s" %(err))
        
        client_socket.connect((host, port))
        client_socket.setblocking(0)

        socket_fd = client_socket.fileno()
        connections[socket_fd] = client_socket

        logger.debug(f"Added a socket: {socket_fd}")
    
    index = 0 % socket_num
    
    # traverse the dependency root
    # create and schedule requests
    for dependency in dependency_root.postorder():
        logger.debug(f"Added {dependency.value} to {index} : {list(connections.keys())[index]}")
        request = serialize_http_request(host, port, f"/{dependency.value}")
        requests.add_request(list(connections.keys())[index], request, dependency.value)
        index = (index + 1) % socket_num

    return connections, requests

def serialize_http_request(host, port, url):
    '''
        Function to serialize outgoing HTTP request.

        Parameters:
            @host - hostname of the target
            @port - port of thetarget
            @url  - resource to request
        
        Output:
            msg - encoded request to send
    '''
    msg = b''
    CRLF = "\r\n"

    msg += "GET ".encode() + url.encode() + ' '.encode() + "HTTP/1.1".encode() + CRLF.encode()
    msg += "HOST: ".encode() + host.encode() 

    if port != "80":
        msg += f":{port}".encode()

    msg += CRLF.encode() + CRLF.encode() 

    return msg

def create_dependency_tree(body):
    '''
        Function to create dependency tree from the received dependency.csv.

        Parameters:
            @body - body of the request to dependency.csv
        
        Output:
            root - root of the dependency tree
    '''
   
    create_file('dependency.csv', body, image_flag=False)

    dependencies = body.strip('\r\n').split('\n')
    logger.debug(f"Dependencies: {dependencies}")

    root = Node()
    root.create(dependencies=dependencies)
    logger.info(f"Created depdency tree")
    
    return root

def initialize_proj_directory():
    '''
        Function to initialize the directory for the downloaded files.
    '''
    isExist = os.path.exists("./proj")
    if isExist:
        shutil.rmtree("./proj")
        logger.info("Deleted ./proj/ folder")
    os.mkdir('./proj')
    logger.info("Initialized ./proj/ folder")

def create_file(filename, data, image_flag=False):
    '''
        Function to create a file on the local disk.

        Parameters:
            @filename   - name of the file to create
            @image_flag - flag to identify if the excpected response is an image or text.
    '''
    flags = ''

    if image_flag:
        flags = 'wb'
    else:
        flags = 'w'

    with open("proj/" + filename, flags) as file:
        file.write(data)

    logger.info(f'File: {filename} is created')

def parse_url(url):
    '''
        Function to get Host and Port of the server.

        Parameters:
            @url - url to parse

        Output:
            host - hostname of the target
            port - port of the target
    '''
    pattern = '([A-Za-z0-9.]+):?([0-9]+)?'
    tokens = re.split(pattern, url)

    logger.debug(f"Tokens: {tokens}")
    host = tokens[1]
    port = tokens[2]

    if port == None:
        port = "80"
    
    return (host, port)
        
def get_dependencies(client_socket, host, port):
    '''
        Function to handle the request to obtain dependencies.

        Parameters:
            @client_socket - socket to send requests
            @host          - host of the target
            @port          - port of the target

        Output:
            dependency_root - root of the created dependency tree
    '''

    # send request to get depdendency.csv
    dependency_url = "/dependency.csv"
    dependency_request = serialize_http_request(host, port, dependency_url)
    client_socket.send(dependency_request)
    logger.info("Dependency request is sent")
    time.sleep(0.1)

    # get dependency.csv from the server
    for response in handle_response(client_socket=client_socket):
        body, content_type, status = response

        if status != 200:
            logger.error(f"File: {dependency_url[1:]} does not exist. Terminating the client.")
            sys.exit(1)

        logger.debug(f"Hanlding dependency response")
     
        if content_type == 'application':
            # body = body.decode()

            logger.debug(f"Dependency body: {body}")
            # parse the dependency file and create n-ary tree of dependencies
            dependency_root = create_dependency_tree(body)

            return dependency_root
        else:
            logger.error("Unsupported content type for dependency file.")

def parse_response(responses, index, offset):
    '''
        Function to get the header and body from the response.

        Parameters:
            @responses   - response received from server.
            @index       - index to begin parsing
            @offset      - offset till the end of the header

        Output:
            header          - header of the response
            body            - body of the response
            content_length  - length of the body in the response
            content_type    - type of the received response
    '''
     
    # select header
    resp_header = responses[index: index + offset].decode()
    # parse header fields
    headers = resp_header.split("\r\n")

    # iterate over headers
    for header in headers:
        # get fields of the header
        fields = header.split(":")
        
        if "HTTP/1.1" in fields[0]:
            status = int(fields[0].split(" ")[1])
            
        # get content length
        if fields[0] == 'Content-Length':
            content_length = int(fields[1].strip(" "))
        # get content type
        if fields[0] == 'Content-Type':
            content_type = fields[1].strip(" ").split('/')[0]

    # select body
    body = responses[index + offset: index + offset + content_length]
    
    # check if it is image
    if content_type != 'image':
        body = body.decode()

    return headers, body, content_length, content_type, status  

def handle_response(client_socket):
    '''
        Generator to handle the responses when pipelining.
        The requests are parsed using "HTTP/1.1" delimeter. 
        
        Parameters:
            @client_socket - socket to send data

        Output:
            body         - body of the response
            content_type - type of the received content
    '''
    
    # initialize array of responses to store
    responses = []
    # initialzie string to store all responses from server
    server_response = b''
    
    # read data from the server
    try:
        while True:
            data = client_socket.recv(BUF_SIZE)
            server_response += data

            # if 0 bytes received, it means client stopped sending
            if  len(data) == 0 and server_response != 0:
                break
    except BlockingIOError:
        pass
    
    logger.info(f"Response obtained: {len(server_response)} bytes")
    
    while True:
        # pattern to select the requests - HTTP/1.1
        pattern = b"\x48\x54\x54\x50\x2f\x31\x2e\x31"
        
        # find index of HTTP/1.1
        index = server_response.find(pattern)
        offset = 1

        while True:
            # get next piece of data and try to parse using CRLFCRLF 
            chunk = server_response[index: index + offset]
            header_index = chunk.find(b'\x0d\x0a\x0d\x0a')
            
            # if header line delimeter is present handle the response
            if header_index != -1:
                logger.info("Found new response")

                # get properties of the response
                
                header, body, content_length, content_type, status = parse_response(server_response, index, offset)
              
                logger.debug(f"Header: {header}")
                logger.debug(f"Content Length: {content_length}; Content-Type: {content_type}")
                
                # updat offset to the end of current response
                offset += content_length
                # delete handled response from the response string
                server_response = server_response[index + offset:]

                # return body and content type of processed request
                yield body, content_type, status
                break
            else:
                offset += 1

        # when all responses are removed from the response string, length of the string is zero
        if len(server_response) == 0:
            break

def communicate(server):
    ''''
        Function to handle the communication with the server.

        Parameters:
            @server - url of the server
    '''

    # get host and port from the url
    host, port = parse_url(server)
    port = int(port)

    # create socket to get dependencies
    try: 
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
    except socket.error as err: 
         logger.error("socket creation failed with error %s" %(err))

    client_socket.connect((host, port))
    client_socket.setblocking(0)
    
    dependency_root = get_dependencies(client_socket=client_socket, host=host, port=port)
    
    # compute number of sockets required to get files 
    # 3 files per socket
    length = dependency_root.length(dependency_root) 
    socket_num = math.ceil(length//3)

    # assign each socket one file using round robin strategy
    connections, requests = round_robin(dependency_root, socket_num, host, port)
    
    # register sockets in the epoll
    # set socket state to EPOLLOUT
    epoll = select.epoll()
    for connection_fd in connections.keys():
        epoll.register(connection_fd, select.EPOLLOUT)
        logger.info(f"{connection_fd} object registered in epoll")
        logger.info(f"Request: {requests.get_queue(connection_fd)}")

    while True:
        events = epoll.poll(1)

        # if all sockets are finished, stop the program
        if len(connections) == 0:
            logger.info("Terminating client")
            break
        
        for file_descriptor, event in events:

            if event & select.EPOLLIN:
                
                handled_responses = 0
                queue = requests.get_queue(file_descriptor)
                
                # read the response
                for index, response in enumerate(handle_response(connections[file_descriptor])):
                        body, content_type, status = response
                        
                        if status != 200:
                            logger.error(f"File {queue[index]} does not exist.")
                        else:    
                            if content_type == 'image':
                                create_file(queue[index], body, image_flag=True)
                            else:
                                create_file(queue[index], body, image_flag=False)

                        handled_responses += 1
            
                # delete the reecived elements from the queue
                if handled_responses:
                    requests.pop(file_descriptor, handled_responses)
                
                # if no elements remains in the queue of this socket
                # unregister the socket 
                if len(requests.get_queue(file_descriptor)) == 0:
                    logger.info(f"Unregistering {file_descriptor} from epoll")
                    epoll.unregister(file_descriptor)

                    logger.info(f"Closing {file_descriptor}")
                    connections[file_descriptor].close()
                    
                    del connections[file_descriptor]
              
            elif event & select.EPOLLOUT:
                # send all requests that are scheduled for this socket - pipelining
                for index, request in requests.get_request(file_descriptor):
                    
                    byteswritten = connections[file_descriptor].send(request)
                    request = request[byteswritten:]

                    requests.set_request(file_descriptor, index, request)

                    logger.info(f"Requesting for {file_descriptor}")
                
                # run clear function
                requests.clear(file_descriptor)

                # check if all requests are sent 
                is_finished = requests.is_finished(file_descriptor)

                # change socket state if all requests are sent
                if is_finished:
                    epoll.modify(file_descriptor, select.EPOLLIN)
                    logger.info(f"Changing to EPOLLIN for {file_descriptor}")
            
            elif event & select.EPOLLHUP:
                # unregister the client from the epoll
                epoll.unregister(file_descriptor)
                logger.info(f"Unregistered: {file_descriptor}")
                del connections[file_descriptor]

if __name__ == "__main__":

    # clear/create project directory
    initialize_proj_directory()
    
    #  initialize parser
    parser = argparse.ArgumentParser("Client.py")

    parser.add_argument("server", action="store", help="IP of the server to request")
    args = parser.parse_args()

    # get url of the server
    server = args.server

    logger.info(f"Server name: {server}")

    # get files
    communicate(server=server) 
    
    logger.info("Finished")





