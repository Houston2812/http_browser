import re
import os
import sys
import time
import math
import socket
import select
import shutil
import argparse
from colorama import Fore
from colorama import Style
from colorama import init as colorama_init

BUF_SIZE = 4096
colorama_init()

class Logger:
  
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
      
    def __init__(self,value = None): 
        self.value=value 
        self.children=[]

    def create(self, dependencies): 
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
        if self.value == value:
            return self

        for child in self.children:
            node = child.find( value)

            if node:
                return node

    def postorder(self):
        yield self

        if len(self.children) != 0:
            for child in self.children:
                yield from child.postorder()
    
    def length(self, root):   
        if len(root.children) == 0:
            return 1
    
        sum = 0
        for child in root.children:
            sum += self.length(child)
       
        return 1 + sum

class Requests:
    def __init__(self) -> None:
        self.requests = {}
        self.queue = {}

    def add_request(self, fd, request, resource):
        if fd not in self.requests.keys():
            self.requests[fd] = []

        if fd not in self.queue.keys():
            self.queue[fd] = []

        self.requests[fd].append(request)
        self.queue[fd].append(resource)

    def get_request(self, fd):
        logger.info(f"Incomind fd: {fd}")
        if fd in self.requests.keys():
            logger.debug(f"Requets for {fd}: {self.requests[fd]}")
            for index, request in enumerate(self.requests[fd]):
                yield index, request
        
    def set_request(self, fd, index, request):
        self.requests[fd][index] = request

    def clear(self, fd):
        requests = set(self.requests[fd])

        requests.discard(b'')
        self.requests[fd] = list(requests)

    def get_queue(self, fd):
        return self.queue[fd]
    
    def set_queue(self, fd, queue):
        self.queue[fd] = queue
    
    def pop(self, fd, indices):
        logger.debug(f"Indices to delete: {indices}")
        while indices:
            del self.queue[fd][0]
            indices -= 1

    def is_finished(self, fd):
        if len(self.requests[fd]) == 0:
            return True
        else:
            return False

logger = Logger()

def round_robin(dependency_root, socket_num, host, port):
    requests = Requests()
    connections = {}

    logger.debug(f"Socket number: {socket_num}")
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

    for dependency in dependency_root.postorder():
        logger.debug(f"Added {dependency.value} to {index} : {list(connections.keys())[index]}")
        request = serialize_http_request(host, port, f"/{dependency.value}")
        requests.add_request(list(connections.keys())[index], request, dependency.value)
        index = (index + 1) % socket_num
    return connections, requests

def serialize_http_request(host, port, url):
    msg = b''
    CRLF = "\r\n"

    msg += "GET ".encode() + url.encode() + ' '.encode() + "HTTP/1.1".encode() + CRLF.encode()
    msg += "HOST: ".encode() + host.encode() 

    if port != "80":
        msg += f":{port}".encode()

    msg += CRLF.encode() + CRLF.encode() 

    return msg

def parse_dependency_response(body):
    logger.warning(f'Body: {body}')
    create_file('dependency.csv', body)

    dependencies = body.strip('\r\n').split('\n')
    logger.debug(f"Dependencies: {dependencies}")

    root = Node()
    root.create(dependencies=dependencies)
    logger.info(f"Created depdency tree")
    
    return root

def initialize_proj_directory():
    shutil.rmtree("./proj")
    logger.info("Deleted ./proj/ folder")
    os.mkdir('./proj')
    logger.info("Initialized ./proj/ folder")

def create_file(filename, data, image_flag=False):
    flags = ''

    if image_flag:
        flags = 'wb'
    else:
        flags = 'w'

    with open("proj/" + filename, flags) as file:
        file.write(data)

    logger.info(f'File: {filename} is created')

    return filename 

def parse_response(response, image_flag=True):
    index = response.find(b'\x0d\x0a\x0d\x0a')

    logger.debug(f"CRLF index: {index}")

    header = response[:index]
    body = response[index+4:]

    if image_flag:
        # logger.debug(f"Body: {body}")
        return header.decode(), body
    else:
        return header.decode(), body.decode()

def parse_url(url):
    # pattern = 'http:\/\/(\w+):?([0-9]+)?\/(\w+)*\/([^#?\s]+)'
    pattern = '(\w+):?([0-9]+)?'
    tokens = re.split(pattern, url)

    logger.debug(f"Tokens: {tokens}")
    host = tokens[1]
    port = tokens[2]

    if port == None:
        port = "80"
    
    return (host, port)

def get_files(client_socket, url):

    created_files = []

    host, port = parse_url(server)
    dependency_url = "/dependency.csv"

    dependency_request = serialize_http_request(host, port, dependency_url)
    # logger.debug(f"Dependency request: {dependency_request}")
    client_socket.send(dependency_request)
    logger.info("Dependency request is sent")
    
    time.sleep(0.1)
    
    responses = handle_response(client_socket=client_socket)
    logger.debug(f"Responses len for dependency: {len(responses)}")
    header, body = parse_response(response=responses[0], image_flag=False)
    logger.info(f"Server response: {header}")
    dependency_root = parse_dependency_response(body)
    logger.debug(f"Dependency table: {dependency_root.postorder()}")

    index_url = '/' + dependency_root.value
    logger.info(f"Root site: {index_url}")
    
    index_request = serialize_http_request(host, port, index_url)
    # logger.debug(f"Index request: {index_request}")
    client_socket.send(index_request)
    logger.info("Index request is sent")

    time.sleep(0.2)

    responses = handle_response(client_socket=client_socket)
    logger.debug(f"Responses len for index: {len(responses)}")
    if ".png"  in dependency_root.value: 
        header, body = parse_response(response=responses[0], image_flag=True)
    else:
        header, body = parse_response(response=responses[0], image_flag=False)

    created_files.append(create_file(dependency_root.value, body))
    
    for element in dependency_root.postorder():
        if len(element.children) == 0:
            if element.value in created_files:
                continue
            else:
                filename = download_files(filenames=[element], client_socket=client_socket)
                created_files.append(filename)
        else:
            filenames = download_files(filenames=element.children, client_socket=client_socket)
            created_files += filenames
            
def communicate(server):
    
    host, port = parse_url(server)
    port = int(port)

    try: 
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
    except socket.error as err: 
         logger.error("socket creation failed with error %s" %(err))

    client_socket.connect((host, port))
    client_socket.setblocking(0)

    epoll = select.epoll()

    dependency_url = "/dependency.csv"
    dependency_request = serialize_http_request(host, port, dependency_url)
    
    client_socket.send(dependency_request)
    logger.info("Dependency request is sent")
    time.sleep(0.1)

    responses = handle_response(client_socket=client_socket)
    logger.debug(f"Responses len for dependency: {len(responses)}")
    header, body = parse_response(response=responses[0], image_flag=False)
    logger.info(f"Server response: {header}")
    dependency_root = parse_dependency_response(body)
    
    length = dependency_root.length(dependency_root) 
    socket_num = math.ceil(length//3)

    connections, requests = round_robin(dependency_root, socket_num, host, port)
    
    for connection_fd in connections.keys():
        epoll.register(connection_fd, select.EPOLLOUT)
        logger.info(f"{connection_fd} object registered in epoll")
        logger.info(f"Request: {requests.get_queue(connection_fd)}")

    while True:
        events = epoll.poll(1)

        if len(connections) == 0:
            logger.info("Terminating client")
            break

        for file_descriptor, event in events:
            if event & select.EPOLLIN:
                responses = handle_response(connections[file_descriptor])
                logger.debug(f"Responses len: {len(responses)}")

                queue = requests.get_queue(file_descriptor)
                for index in range(len(responses)):
                    
                    header, body = None, None

                    if ".png" in queue[index]:
                        image_flag = True
                    else:
                        image_flag = False

                    header, body = parse_response(response=responses[index], image_flag=image_flag)
                    create_file(queue[index], body, image_flag=image_flag)

                    logger.info(f"Server response: {header}")

                if responses:
                        requests.pop(file_descriptor, len(responses))
                        
                if len(requests.get_queue(file_descriptor)) == 0:
                    logger.info(f"Unregistering {file_descriptor} from epoll")
                    epoll.unregister(file_descriptor)

                    logger.info(f"Closing {file_descriptor}")
                    connections[file_descriptor].close()
                    
                    del connections[file_descriptor]
                
            elif event & select.EPOLLOUT:
                for index, request in requests.get_request(file_descriptor):
                    
                    byteswritten = connections[file_descriptor].send(request)
                    request = request[byteswritten:]

                    requests.set_request(file_descriptor, index, request)

                    logger.info(f"Requesting by {file_descriptor}")
                
                requests.clear(file_descriptor)

                is_finished = requests.is_finished(file_descriptor)

                if is_finished:
                    epoll.modify(file_descriptor, select.EPOLLIN)
                    logger.info(f"Changing to EPOLLIN for {file_descriptor}")
            
            elif event & select.EPOLLHUP:
                # unregister the client from the epoll
                epoll.unregister(file_descriptor)
                logger.info(f"Unregistered: {file_descriptor}")
                del connections[file_descriptor]
                

def download_files(filenames, client_socket):
    logger.debug(f"Filenames: {filenames}")

    requests = []
    created_files = []

    for filename in filenames:
        try:
            sub_url = '/' + filename.value
        except:
            logger.warning(f"Wrong value for filename: {filename}")

        logger.debug(f"Sub url:  {sub_url}")
        sub_request = serialize_http_request(host, port, sub_url)
        client_socket.send(sub_request)
        # logger.info(f"Sub request: {sub_request} is sent")

        requests.append(filename.value)

    time.sleep(0.1)
    responses = handle_response(client_socket=client_socket)
    logger.info(f"Obtained resposnes: {len(responses)}")

    for index, request in enumerate(requests):
        if '.png' in request:
            image_flag = True
        else:
            image_flag = False
        
        logger.info(f"Parsing response {index}")
        header, body = parse_response(responses[index], image_flag=image_flag)
        # logger.debug(header)

        created_files.append(create_file(request, body, image_flag=image_flag))

    return created_files

def handle_response(client_socket):
    responses = []
    server_response = b''
    
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

    http_pattern = b'\x48\x54\x54\x50\x2f\x31\x2e\x31\x20\x32\x30\x30\x20\x4f\x4b'
    offset = 0
    indices = []
    
    while True:
        index = server_response[offset:].find(http_pattern)
    
        if index != -1:
            indices.append(index + offset)
        else:
            indices.append(index)
        
        offset = offset + index + len(http_pattern)
        if index == -1:
            break

    logger.info(f"Response parsed to indices: {indices}")    

    for index, val in enumerate(indices):
        if index == 0:
            continue

        if indices[index] == -1:
            response = server_response[indices[index-1]:]
        else: 
            response = server_response[indices[index-1]:indices[index]]
        responses.append(response)

    return responses

def get_response(client_socket, decode=True ):
    server_response = b''
    header = b''
    body = b''

    try:
        while True:
            data = client_socket.recv(BUF_SIZE)
            server_response += data

            # if 0 bytes received, it means client stopped sending
            if  len(data) == 0 and server_response != 0:
                break
    except BlockingIOError:
        pass
    
    logger.warning(server_response)
    logger.error(server_response.decode())

    header, body = parse_response(server_response, False)

    return header, body
    
if __name__ == "__main__":

    initialize_proj_directory()
    parser = argparse.ArgumentParser("Client.py")

    parser.add_argument("server", action="store", help="IP of the server to request")

    args = parser.parse_args()

    server = args.server

    logger.info(server)


    communicate(server=server)
    # try: 
    #     clientSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
    # except socket.error as err: 
    #     logger.error("socket creation failed with error %s" %(err))

    # host, port = parse_url(server)

    # clientSock.connect((host, int(port)))
    # clientSock.setblocking(0)

    # request = get_files(client_socket= clientSock, url = server)
    logger.info("Finished")





