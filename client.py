import re
import os
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
    logger.warning(f'Body: {body}')
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


def parse_response(response, image_flag=True):
    '''
        Function to get the header and body from the response.

        Parameters:
            @response   - response received from server.
            @image_flag - flag to identify if the excpected response is an image or text.

        Output:
            header - header of the response
            body   - body of the response
    '''
    index = response.find(b'\x0d\x0a\x0d\x0a')

    logger.debug(f"CRLF index: {index}")

    header = response[:index]
    body = response[index+4:]

    logger.debug(f"Header: {header.decode()}")

    return header.decode(), body

    # if image_flag:
    #     # logger.debug(f"Body: {body}")

    #     return header.decode(), body
    # else:
    #     return header.decode(), body.decode()

def parse_url(url):
    '''
        Function to get Host and Port of the server.

        Parameters:
            @url - url to parse

        Output:
            host - hostname of the target
            port - port of the target
    '''
    pattern = '(\w+):?([0-9]+)?'
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
    responses = handle_response(client_socket=client_socket)
    logger.debug(f"Responses len for dependency: {len(responses)}")
    # parse the response 
    header, body = parse_response(response=responses[0])

    # get content type of the response
    content_type = get_content_type(header)
    
    if content_type == 'application':
        body = body.decode()

        logger.debug(f"Dependency body: {body}")
        # parse the dependency file and create n-ary tree of dependencies
        dependency_root = create_dependency_tree(body)

        return dependency_root
    else:
        logger.error("Unsupported content type for dependency file.")

def handle_response(client_socket):
    '''
        Function to handle the responses when pipelining.
        The requests are parsed using "HTTP 1.1 200 OK" delimeter. 
        
        Parameters:
            @client_socket - socket to send data

        Output:
            responses - array of the responses to obtain
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
    
    logger.info(f"Response obtained")

    # delimiter is hex form of "HTTP 1.1 200 OK"
    http_pattern = b'\x48\x54\x54\x50\x2f\x31\x2e\x31\x20\x32\x30\x30\x20\x4f\x4b'
    
    # offset used to parse the data
    offset = 0
    # array of indices to not where string will be parsed
    indices = []
    
    while True:
        # get index of the pattern
        index = server_response[offset:].find(http_pattern)

        # store index
        if index != -1:
            indices.append(index + offset)
        else:
            indices.append(index)
        
        # calculate offset
        offset = offset + index + len(http_pattern)

        # stop if end was reached
        if index == -1:
            break

    logger.info(f"Response parsed to indices: {indices}")    

    # iterate over indices and divide responses
    for index, val in enumerate(indices):
        if index == 0:
            continue

        if indices[index] == -1:
            response = server_response[indices[index-1]:]
        else: 
            response = server_response[indices[index-1]:indices[index]]
        responses.append(response)

    return responses

def get_content_type(response_header):
    '''
        Function to get the content type of the response.

        Parameters:
            @header - header of the resposne
        
        Output:
            content_type - type of the content
    '''

    headers = response_header.split('\r\n')
    for header in headers:

        fields = header.split(':')

        # to filter out status line
        if len(fields) <= 1:
            continue

        key = fields[0]
        value = fields[1:]

        if key == 'Content-Type':
            content_type = value[0].strip(' ').split("/")[0]
            logger.debug(f"Content Type: {content_type}")
            return content_type

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
                # read the response
                responses = handle_response(connections[file_descriptor])
                logger.debug(f"Responses len: {len(responses)}")

                # get list of expected files for this socket
                queue = requests.get_queue(file_descriptor)
                for index in range(len(responses)):
                    
                    header, body = None, None

                    # if ".png" in queue[index]:
                    #     image_flag = True
                    # else:
                    #     image_flag = False

                    # parse the response
                    header, body = parse_response(response=responses[index])

                    # get content type
                    content_type = get_content_type(header)

                    # create file   
                    if content_type == 'text' or content_type == 'application':
                        body = body.decode()
                        create_file(queue[index], body, image_flag=False)
                    elif content_type == 'image':
                        create_file(queue[index], body, image_flag=True)
                    else:
                        logger.error("Unsupported content type.")

                # delete the reecived elements from the queue
                if responses:
                        requests.pop(file_descriptor, len(responses))
                    
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

                    logger.info(f"Requesting by {file_descriptor}")
                
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





