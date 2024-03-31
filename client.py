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

def serialize_http_request(url):
    msg = b''
    CRLF = "\r\n"

    host, port, url = parse_url(server)
    
    msg += "GET ".encode() + url.encode() + ' '.encode() + "HTTP/1.1".encode() + CRLF.encode()
    msg += "HOST: ".encode() + host.encode() 

    if port != "80":
        msg += f":{port}".encode()

    msg += CRLF.encode()
    # msg += "Connection: Keep-Alive".encode() + CRLF.encode()
    # msg += "Content-Type: text/html".encode() + CRLF.encode()
    
    msg += CRLF.encode() 

    return msg

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
    pattern = '^http:\/\/(\w+):?([0-9]+)?(\/[^#?\s]+)'

    tokens = re.split(pattern, url)

    host = tokens[1]
    port = tokens[2]
    url = tokens[3]

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

    request = serialize_http_request(server)

    log(f"Request: {request}", 'debug')

    host, port, _ = parse_url(server)

    clientSock.connect((host, int(port)))
    clientSock.setblocking(0)

    clientSock.send(request)
    log("Request is sent", "info")
    
    time.sleep(1)
    server_response = b''

    try:
        try:
            while True:
                data = clientSock.recv(BUF_SIZE)
                server_response += data

                # if 0 bytes received, it means client stopped sending
                if  len(data) == 0 and server_response != 0:
                    break
        except BlockingIOError:
            pass

    except KeyboardInterrupt:
        log(f"Finished", "info")
        
    log(f"Server response: {server_response}", 'info')
    






