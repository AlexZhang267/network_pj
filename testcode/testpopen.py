import subprocess
if __name__=='__main__':
	args=['python3','../http_part/httpresolver.py','baidu.com']
	# args = ['curl']
	out = open('out.txt','w')
	subprocess.Popen(args=args,stdout=out)
	out.close()