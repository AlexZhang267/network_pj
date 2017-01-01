#coding=utf-8
import time
import socket
import random


	#



def dns_lookup(uri):
	s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	# s.settimeout(10)
	dns_address = ("202.120.224.26",53)
	start = time.time()
	msg = b'\x5c\x6d\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00\x03www\x05baidu\x03com\x00\x00\x01\x00\x01'
	s.sendto(msg, dns_address)

	try:
		data, server = s.recvfrom(1024)
		end = time.time()
		elapsed = end - start
		print(len(data))
		print(data.decode('utf-8'),elapsed)

	except Exception as e:
		print(e)
		print('REQUEST TIMED OUT')

if __name__ == '__main__':
	dns_lookup("www.baidu.com")