import re
import os
import sys
import shutil
import time
import socket
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
        # print(f"{self.colors[level]}client.py - {level.upper()} - {self.signs[level]} {msg}{Style.RESET_ALL}")
        pass

    def warning(self, msg=''):
        level = 'warning'
        print(f"{self.colors[level]}client.py - {level.upper()} - {self.signs[level]} {msg}{Style.RESET_ALL}")

    def error(self, msg=''):
        level = 'error'
        print(f"{self.colors[level]}client.py - {level.upper()} - {self.signs[level]} {msg}{Style.RESET_ALL}")

logger = Logger()

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

def handle_proj_directory():
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
    # if filename=='image(10).png':
    #     sys.exit()
        

    return filename 

def send_data(client_socket, requests, responses):
    for request in requests:
        client_socket.send(request)
        responses.append([])

    requests.clear()

def send_request(client_socket, url):

    requests = []
    responses = []
    
    created_files = []

    host, port = parse_url(server)

    dependency_url = "/dependency.csv"

    dependency_request = serialize_http_request(host, port, dependency_url)
    logger.debug(f"Dependency request: {dependency_request}")

    requests.append(dependency_request)
    
    send_data(client_socket=client_socket, requests=requests, responses=responses)
    logger.info("Dependency request is sent")
    
    time.sleep(1)

  
    header, body = get_response(client_socket=client_socket)

    logger.info(f"Server response: {header}")
    dependency_root = parse_dependency_response(body)

    logger.debug(f"Dependency table: {dependency_root.postorder()}")

    index_url = '/' + dependency_root.value
    logger.info(f"Root site: {index_url}")
    
    index_request = serialize_http_request(host, port, index_url)
    
    logger.debug(f"Index request: {index_request}")

    client_socket.send(index_request)
    logger.info("Index request is sent")

    time.sleep(0.2)
    header, body = get_response(client_socket=client_socket)

    created_files.append(create_file(dependency_root.value, body))

    for element in dependency_root.postorder():
        
        logger.warning(f"Created files: {created_files}")
        if len(element.children) == 0:
            if element.value in created_files:
                continue
            else:
                filename = download_files(filenames=[element], client_socket=client_socket)
                created_files.append(filename)
        else:

            filenames = download_files(filenames=element.children, client_socket=client_socket)

            created_files += filenames
            

def download_files(filenames, client_socket):

    logger.debug(f"Filenames: {filenames}")

    requests = []
    created_files = []
    for filename in filenames:

        try:
            sub_url = '/' + filename.value
        except:
            logger.warning(f"Filename: {filename}")

        logger.debug(f"Sub url:  {sub_url}")

        sub_request = serialize_http_request(host, port, sub_url)

        client_socket.send(sub_request)
        logger.info(f"Sub request: {sub_request} is sent")

        requests.append(filename.value)
    
    # server_response = handle_response(client_socket=client_socket)
    time.sleep(0.1)
    responses = handle_response(client_socket=client_socket)
    
    # logger.error(f"Responses: {responses}")
    for index, request in enumerate(requests):

        if '.png' in request:
            image_flag = True
        else:
            image_flag = False
        
         
        # logger.warning(f"Request to decode: {request}; Response: {responses[index]} Flag: {image_flag}")
        header, body = parse_response(responses[index], image_flag=image_flag)

        logger.warning(body)
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
    
    # http_pattern = b'\x48\x54\x54\x50\x2f\x31\x2e\x31'
    http_pattern = b'\x48\x54\x54\x50\x2f\x31\x2e\x31\x20\x32\x30\x30\x20\x4f\x4b'

    offset = 0

    indices = []
    
    # logger.warning(server_response)

    while True:

        index = server_response[offset:].find(http_pattern)
    
        if index != -1:
            indices.append(index + offset)
        else:
            indices.append(index)
        
        offset = offset + index + len(http_pattern)
        
      
        if index == -1:
            break
    logger.warning(f"Indices: {indices}")

    for index, val in enumerate(indices):
        if index == 0:
            continue
        logger.info(f"Index: {index-1}, {index}")

        if indices[index] == -1:
            response = server_response[indices[index-1]:]
        else: 
            response = server_response[indices[index-1]:indices[index]]
        responses.append(response)

    return responses

def parse_response(response, image_flag=True):
    index = response.find(b'\x0d\x0a\x0d\x0a')

    logger.debug(f"CRLF index: {index}")

    header = response[:index]
    body = response[index+4:]

    if image_flag:
        logger.debug(f"Body: {body}")
        return header.decode(), body
    else:
        return header.decode(), body.decode()


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
    # index = server_response.find(b'\x0d\x0a\x0d\x0a')
    
    # logger.debug(f'Parse index: {index}')
    # header = server_response[:index]
    # body = server_response[index+4:]

    # if not decode:
    #     logger.debug(f"Body: {body}")
    #     return header.decode(), body
    # else:
    #     return header.decode(), body.decode()

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

if __name__ == "__main__":

    handle_proj_directory()
    parser = argparse.ArgumentParser("Client.py")

    parser.add_argument("server", action="store", help="IP of the server to request")

    args = parser.parse_args()

    server = args.server

    logger.info(server)

    try: 
        clientSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
    except socket.error as err: 
        logger.error("socket creation failed with error %s" %(err))

    host, port = parse_url(server)

    clientSock.connect((host, int(port)))
    clientSock.setblocking(0)

    request = send_request(client_socket= clientSock, url = server)






