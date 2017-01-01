import os
import sys
import struct
import socket
import threading
import time
from multiprocessing import Queue
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


def build_request(address, qtype=1):
    if type(address) != bytes:
        address = address.encode('utf8')
    request_id = os.urandom(2)
    header = struct.pack('!BBHHHH', 1, 0, 1, 0, 0, 0)
    addr = build_address(address)
    qtype_qclass = struct.pack('!HH', qtype, 1)
    return request_id + header + addr + qtype_qclass


def parse_ip(addrtype, data, length, offset):
    if addrtype == 1:
        return socket.inet_ntop(socket.AF_INET, data[offset:offset + length])
    elif addrtype == 28:
        return socket.inet_ntop(socket.AF_INET6, data[offset:offset + length])
    else:
        return None


def parse_name(data, offset):
    p = offset
    labels = []
    if type(data[p]) == int:
        l = data[p]
    else:
        l = ord(data[p])
    while l > 0:
        if (l & (128 + 64)) == (128 + 64):
            # pointer
            pointer = struct.unpack('!H', data[p:p + 2])[0]
            pointer &= 0x3FFF
            r = parse_name(data, pointer)
            labels.append(r[1])
            p += 2
            # pointer is the end
            return p - offset, b'.'.join(labels)
        else:
            labels.append(data[p + 1:p + 1 + l])
            p += 1 + l
        if type(data[p]) == int:
            l = data[p]
        else:
            l = ord(data[p])

    return p - offset + 1, b'.'.join(labels)


def parse_record(data, offset, question=False):
    nlen, name = parse_name(data, offset)
    if not question:
        record_type, record_class, record_ttl, record_rdlength = struct.unpack(
            '!HHiH', data[offset + nlen:offset + nlen + 10]
        )
        ip = parse_ip(record_type, data, record_rdlength, offset + nlen + 10)
        if ip is not None:
            return nlen + 10 + record_rdlength, \
                   (name, ip, record_type, record_class, record_ttl)
        else:
            return nlen + 10 + record_rdlength, \
                   False
    else:
        record_type, record_class = struct.unpack(
            '!HH', data[offset + nlen:offset + nlen + 4]
        )
        return nlen + 4, (name, None, record_type, record_class, None, None)


def parse_header(data):
    if len(data) >= 12:
        header = struct.unpack('!HBBHHHH', data[:12])
        res_id = header[0]
        res_qr = header[1] & 128
        res_tc = header[1] & 2
        res_ra = header[2] & 128
        res_rcode = header[2] & 15
        # assert res_tc == 0
        # assert res_rcode in [0, 3]
        res_qdcount = header[3]
        res_ancount = header[4]
        res_nscount = header[5]
        res_arcount = header[6]
        return (res_id, res_qr, res_tc, res_ra, res_rcode, res_qdcount,
                res_ancount, res_nscount, res_arcount)
    return None


def parse_response(data):
    try:
        if len(data) >= 12:
            header = parse_header(data)
            if not header:
                return None
            res_id, res_qr, res_tc, res_ra, res_rcode, res_qdcount, \
            res_ancount, res_nscount, res_arcount = header

            qds = []
            ans = []
            offset = 12
            for i in range(0, res_qdcount):
                l, r = parse_record(data, offset, True)
                offset += l
                if r:
                    qds.append(r)
            for i in range(0, res_ancount):
                l, r = parse_record(data, offset)
                offset += l
                if r:
                    ans.append(r)
            for i in range(0, res_nscount):
                l, r = parse_record(data, offset)
                offset += l
            for i in range(0, res_arcount):
                l, r = parse_record(data, offset)
                offset += l
            response = DNSResponse()
            if qds:
                response.hostname = qds[0][0]
            for an in qds:
                response.questions.append((an[1], an[2], an[3]))
            for an in ans:
                response.answers.append((an[1], an[2], an[3]))
            return response
    except Exception as e:
        return None


class DNSResponse(object):
    def __init__(self, qtype = 1):
        self.hostname = None
        self.questions = []
        self.answers = []
        self._qtype = qtype

    def set_qtype(self,qtype):
        self._qtype = qtype

    def get_qtype(self):
        return self._qtype


class DNSClient(object):
    def __init__(self, uri=None, ipv6=False):
        self._uri = uri
        self._ipv6 = ipv6
        self._dns_address = ("202.120.224.26", 53)
        self.responseQ = Queue()

    def __dns_lookup(self, host, stop_event, qtype=1):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(5)

        req = build_request(host, qtype=qtype)
        try:
            s.sendto(req, self._dns_address)
            data, server = s.recvfrom(1024)
        except Exception as e:
            sys.stderr.write(type(e.reason))
            pass

        # parse response
        dns_response = parse_response(data)
        dns_response.set_qtype(qtype)
        answer_len = len(dns_response.answers)

        if not stop_event.is_set() and answer_len!=0:
            stop_event.set()
            self.responseQ.put(dns_response)
            sys.stderr.write(str(dns_response.answers))

    def dns_lookup(self, host):
        a_stop_event = threading.Event()
        t1 = threading.Thread(target=self.__dns_lookup,args=(host,a_stop_event,1))
        t2 = threading.Thread(target=self.__dns_lookup,args=(host,a_stop_event,28))
        t1.start()
        t2.start()

        while not a_stop_event.is_set():
            time.sleep(0.01)
            if not t1.is_alive() and not t2.is_alive():
                break

        # dns_response = self.responseQ.get()
        # sys.stderr.write(str(dns_response.answers))
        # return dns_response
        return self.responseQ

if __name__ == '__main__':
    dc = DNSClient()
    r = dc.dns_lookup('http://pj-test.htcnet.moe:8032/test/10')
    # print(r.answers)
