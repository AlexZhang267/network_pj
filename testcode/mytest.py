#coding=utf-8

import socket
import struct
import os


def to_bytes(s):
    if bytes != str:
        if type(s) == str:
            return s.encode('utf-8')
    return s

# def patch_socket():
#     if not hasattr(socket, 'inet_pton'):
#         socket.inet_pton = to_bytes(socket.inet_ntoa(ipstr))
#
#     if not hasattr(socket, 'inet_ntop'):
#         socket.inet_ntop = inet_ntop
#
#
# patch_socket()


def test_dns():
    try:
        ips = socket.gethostbyname_ex("www.baidu.com")
    except socket.gaierror:
        ips = []
    return ips


def test_header():
    header = struct.pack('!BBHHHH', 1, 0, 1, 0, 0, 0)
    print(header)

def build_address(address):
    address = address.strip(b'.')
    labels = address.split(b'.')
    results = []
    for label in labels:
        l = len(label)
        if l > 63:
            return None
        results.append(chr(l).encode('utf-8'))
        results.append(label)
    results.append(b'\0')
    return b''.join(results)

def build_request(address, qtype):
    request_id = os.urandom(2)
    header = struct.pack('!BBHHHH', 1, 0, 1, 0, 0, 0)
    addr = build_address(address)
    qtype_qclass = struct.pack('!HH', qtype, 1)
    return request_id + header + addr + qtype_qclass

def main():
    test = build_request(b'baidu.com',1)
    print(test)
if __name__ == "__main__":
    main()