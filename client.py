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

def parse_response(response):
    dependency_table = {}

    response = response.decode()

    CRLF = "\r\n"

    header, body = response.split(CRLF + CRLF)

    dependencies = body.rstrip('\n').split('\n')

    log(f"Dependencies: {dependencies}", 'debug')

    for dependency in dependencies:
        elements = dependency.split(',')
        log(f"Elements: {elements}", 'debug')
        if len(elements[1]) == 0:
            dependency_table[elements[0].strip(',')] = []
        else:
            dependency_table[elements[1].strip(',')].append(elements[0].strip(','))

    return dependency_table



def send_request(url):
    host, port, url_elements = parse_url(server)
    
    log(f"URL elements: {url_elements}", "debug")

    dependency_url = "/" + url_elements[0] + "/dependency.csv"

    dependency_request = serialize_http_request(host, port, dependency_url)
    log(f"Dependency request: {dependency_request}", 'debug')

    clientSock.send(dependency_request)
    log("Dependency request is sent", "info")
    
    time.sleep(1)
    dependency_response = get_response()  
        
    log(f"Server response: {dependency_response}", 'info')
    
    dependencies = parse_response(dependency_response)

    log(f"Dependency table: {dependencies}", 'debug')
    

def get_response():
    server_response = b''
    try:
        while True:
            data = clientSock.recv(BUF_SIZE)
            server_response += data

            # if 0 bytes received, it means client stopped sending
            if  len(data) == 0 and server_response != 0:
                break
    except BlockingIOError:
        pass
    
    return data

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
    pattern = 'http:\/\/(\w+):?([0-9]+)?\/(\w+)*\/([^#?\s]+)'

    tokens = re.split(pattern, url)

    host = tokens[1]
    port = tokens[2]
    url = tokens[3:-1]

    if port == None:
        port = "80"
    
    return (host, port, url)

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

    host, port, _ = parse_url(server)

    clientSock.connect((host, int(port)))
    clientSock.setblocking(0)

    request = send_request(server)






