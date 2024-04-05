import binascii

def parse_response(responses, index, offset):
    resp_header = responses[index: index + offset].decode()
    headers = resp_header.split("\n")
    for header in headers:
        fields = header.split(":")
        if fields[0] == 'Content-Length':
            content_length = int(fields[1].strip(" "))
            break
        if fields[0] == 'Content-Type':
            content_type = fields[1].strip(" ").split('/')[0]

    body = responses[index + offset: index + offset + content_length]

    if content_type != 'image':
        body = body.decode()
    
    return header, body, content_length, content_type  

def get_responses(responses):

    while True:
        if len(responses) == 0:
            break
        pattern = b"\x48\x54\x54\x50\x2f\x31\x2e\x31"
        index = responses.find(pattern)
        offset = 1

        while True:
            chunk = responses[index: index + offset]
            header_index = chunk.find(b'\x0d\x0a\x0d\x0a')
            
            if header_index != -1:
                print("Found")

                header, body, content_length, content_type = parse_response(responses, index, offset)

            
                if content_type == 'image':
                    with open(f'file-{offset}', 'wb') as file:
                        file.write(body)
                else:
                    with open(f'file-{offset}', 'w') as file:
                        file.write(body)
                
                
                offset += content_length
                responses =  responses[index + offset:]
                yield body, content_type
                break
            else:
                offset += 1

if __name__ == "__main__":

    responses = b''
    with open("response", 'rb') as file:
        responses = file.read()

    print(len(responses))

    for index, response in  enumerate(get_responses(responses)):
        body, content_type =response

        print(f"Index: {index}; Content Type: {content_type}")
        # print(f"Body: {body}")