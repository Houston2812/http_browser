import re
import sys
import time
import socket
import argparse
from colorama import Fore
from colorama import Style
from colorama import init as colorama_init


BUF_SIZE = 4096
colorama_init()

def serialize_http_request(host, port, url):
    msg = b''
    CRLF = "\r\n"

    msg += "GET ".encode() + url.encode() + ' '.encode() + "HTTP/1.1".encode() + CRLF.encode()
    msg += "HOST: ".encode() + host.encode() 

    if port != "80":
        msg += f":{port}".encode()

    msg += CRLF.encode()
    # msg += "Connection: Keep-Alive".encode() + CRLF.encode()
    # msg += "Content-Type: text/html".encode() + CRLF.encode()
    
    msg += CRLF.encode() 

    return msg
# http:\/\/(\w+):?([0-9]+)?(\/[\w\-\.]+[^#?\s]+)

def parse_dependency_response(body):
    dependency_table = {}

    
    log(f'Body: {body}', 'warning')
    create_file('dependency.csv', body)

    dependencies = body.strip('\r\n').split('\n')

    log(f"Dependencies: {dependencies}", 'debug')

    for dependency in dependencies:
        elements = dependency.split(',')
        log(f"Elements: {elements}", 'debug')
        if len(elements[1]) == 0:
            key = elements[0].strip(',')
            dependency_table[key] = []
        else:
            key = elements[1].strip(',')
            value = elements[0].strip(',')
            
            dependency_table[key].append(value)
            dependency_table[value] = []

    return dependency_table

def create_file(filename, data, bytes=False):
    flags = ''

    if bytes:
        flags = 'wb'
    else:
        flags = 'w'

    with open("proj/" + filename, flags) as file:
        file.write(data)

    log(f'File: {filename} is created', 'info')

def send_request(url):
    host, port = parse_url(server)

    dependency_url = "/dependency.csv"

    dependency_request = serialize_http_request(host, port, dependency_url)
    log(f"Dependency request: {dependency_request}", 'debug')

    clientSock.send(dependency_request)
    log("Dependency request is sent", "info")
    
    time.sleep(1)
    header, body = get_response()
        
    log(f"Server response: {header}", 'info')
    
    dependencies = parse_dependency_response(body)

    log(f"Dependency table: {dependencies}", 'debug')

    index_url = '/' + list(dependencies.keys())[0]
    log(f"Root site: {index_url}", 'info')
    
    index_request = serialize_http_request(host, port, index_url)
    log(f"Index request: {index_request}", 'debug')

    clientSock.send(index_request)
    log("Index request is sent", "info")

    time.sleep(0.2)
    header, body = get_response()

    create_file(list(dependencies.keys())[0], body)

    for key, values in dependencies.items():
        for value in values:

            sub_url = '/' + value
            
            log(f"Sub url:  {sub_url}", 'debug')

            sub_request = serialize_http_request(host, port, sub_url)
            log(f"Sub request: {sub_request}", 'debug')

            clientSock.send(sub_request)
            log("Sub request is sent", 'info')

            time.sleep(0.5)
            byte_flag = False
            if '.png' in value:
                header, body = get_response(decode=False)
                byte_flag = True
            else:
                header, body = get_response()
            
            create_file(value, body, bytes=byte_flag)


def get_response(decode=True):
    server_response = b''
    header = b''
    body = b''

    try:
        while True:
            data = clientSock.recv(BUF_SIZE)


            server_response += data

            # if 0 bytes received, it means client stopped sending
            if  len(data) == 0 and server_response != 0:
                break
    except BlockingIOError:
        pass
    
    index = server_response.find(b'\x0d\x0a\x0d\x0a')
    
    log(f'Parse index: {index}', 'debug')
    header = server_response[:index]
    body = server_response[index+4:]

    if not decode:
        log(f"Body: {body}", 'debug')
        return header.decode(), body
    else:
        return header.decode(), body.decode()

def log(msg, level):
    colors = {
        'debug': Fore.BLUE,
        'info': Fore.GREEN,
        'warning': Fore.YELLOW,
        'error': Fore.RED,
        'message': Fore.BLACK
    }

    signs = {
        'debug' : '[-]',
        'info': '[+]',
        'warning' : '[!]',
        'error': '[!!]',
        'message': '[...]'
    }

    color = colors[level]
    sign = signs[level]

    print(f"{color}client.py - {level.upper()} - {sign} {msg}{Style.RESET_ALL}")

def parse_url(url):
    # pattern = 'http:\/\/(\w+):?([0-9]+)?\/(\w+)*\/([^#?\s]+)'
    pattern = '(\w+):?([0-9]+)?'
    tokens = re.split(pattern, url)

    log(f"Tokens: {tokens}", 'debug')
    host = tokens[1]
    port = tokens[2]

    if port == None:
        port = "80"
    
    return (host, port)

if __name__ == "__main__":
    parser = argparse.ArgumentParser("Client.py")

    parser.add_argument("server", action="store", help="IP of the server to request")

    args = parser.parse_args()

    server = args.server

    log(server, 'info')

    try: 
        clientSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
    except socket.error as err: 
        log("socket creation failed with error %s" %(err), 'error')

    host, port = parse_url(server)

    clientSock.connect((host, int(port)))
    clientSock.setblocking(0)

    request = send_request(server)






