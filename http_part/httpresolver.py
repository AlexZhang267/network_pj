# coding=utf8
import socket
import io
import gzip
import sys
from uri_parser import parser
from dns_client.dns_client import DNSClient


class HttpResponse(object):
    def __init__(self, data):
        self.data = data
        # self.__parse_response()
        self.start_line, self.message_body = self.__parse_response()

    def __parse_response(self):
        if type(self.data) != bytes:
            self.data = self.data.encode('utf8')
        crlf = self.data.find(b"\r\n\r\n")
        if crlf==-1:
            return '',''
        self.start_line = self.data[0:crlf + 4]
        self.message_body = self.data[crlf + 4:]
        self.header = self.__parse_header()
        encoding = self.header.get(b'Content-Encoding')

        transfer_coding = self.header.get(b'Transfer-Encoding')

        content_length = self.header.get(b'Content-Length')

        # 检查是否有chunk
        if transfer_coding == b' chunked':
            self.message_body = self.__decode_chunked()

        # 检查是否是gzip压缩的
        if encoding == b' gzip':
            self.__decode_gzip()

        # sys.stderr.write(content_length)
        # sys.stderr.write("+++++++")

        return self.start_line, self.message_body

    def __parse_header(self):
        tmp = self.start_line.split(b'\r\n')
        header = dict()
        for tt in tmp:
            tt = tt.split(':')
            if len(tt) > 1:
                header[tt[0]] = tt[1]
        return header

    def __decode_gzip(self):
        buf = io.BytesIO(self.message_body)
        f = gzip.GzipFile(fileobj=buf)
        self.message_body = f.read()

    def __decode_chunked(self):
        # r = True
        chunk_data = ''
        while 1:
            index = self.message_body.find(b'\r\n')
            chunk_size = int(self.message_body[:index], 16)
            if chunk_size <= 0:
                break
            # elif chunk_size<0:
            #     break

            chunk_data += self.message_body[index + 2:index + 2 + chunk_size]
            self.message_body = self.message_body[index + 2 + chunk_size + 2:]
        return chunk_data


class HttpResolver(object):
    def __init__(self):
        self.get_method = b'GET'
        self.sp = b' '
        self.version = b'HTTP/1.1'
        self.cr = b'\r'
        self.lf = b'\n'
        self.host = b'Host: '
        self.connection = b'Connection: '
        self.cache_control = b'http_part.cache_control: '
        self.user_agent = b'User-Agent: '
        self.accept = b'Accept: '
        self.accept_language = b'Accept_Language: '
        self.accept_encoding = b'Accept-Encoding: '
        # self.default_connection = b'keep-alive\r\n'
        self.default_connection = b'close\r\n'
        self.default_cache_control = b'max-age=0\r\n'
        self.default_user_agent = b'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.95 Safari/537.36\r\n'
        self.default_accept = b'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8\r\n'
        self.default_accept_encoding = b'identity\r\n'
        # self.default_accept_encoding = b'gzip, deflate, sdch\r\n'
        self.default_accept_language = b'en-US,en;q=0.8,zh-CN;q=0.6,zh;q=0.4\r\n'
        pass

    def build_request_line(self, parse_res):
        path = parse_res[2]
        path = path.encode('utf8')
        return self.get_method + self.sp + path + self.sp + self.version + self.cr + self.lf

    def build_header(self, parse_res):
        host = parse_res[1].encode('utf8') + self.cr + self.lf
        return self.accept_encoding + self.default_accept_encoding + self.host + host + self.connection + self.default_connection

    def build_get_request(self, parse_res):
        request_line = self.build_request_line(parse_res)
        header = self.build_header(parse_res)
        return request_line + header + self.cr + self.lf

    def get(self, url):
        res = parser.parse_uri(uri=url)
        scheme = res[0]
        sys.stderr.write(res[0])
        sys.stderr.write("%%%%")

        request = self.build_get_request(res)
        sys.stderr.write(request)

        host = res[1]
        tmp = host.split(':')
        port = -1
        if len(tmp) > 1:
            host = tmp[0]
            port = int(tmp[1])

        dns_client = DNSClient()
        response_queue = dns_client.dns_lookup(host=host)
        ip = '0'
        response = ''
        while not response_queue.empty():
            dns_response = response_queue.get()
            for answer in dns_response.answers:
                try:
                    if len(answer)!=0:
                        ip = answer[0]
                        break
                except Exception:
                    pass

            if dns_response.get_qtype()==1:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            else:
                s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
            s.settimeout(5)
            if scheme=='http':
                if port == -1:
                    port = 80

                try:
                    s.connect((ip, port))
                    s.send(request)
                    while 1:
                        data = s.recv(1024)
                        if not len(data):
                            break
                        response += data
                    break
                except Exception as e:
                    # sys.stderr.write(str(e))
                    pass
            elif scheme == 'https':
                if port==-1:
                    port = 443
                try:
                    s.connect((ip, port))
                    ssl_socket = socket.ssl(s)
                    ssl_socket.write(request)

                    while 1:
                        # data = s.recv(1024)
                        data = ssl_socket.read(1024)
                        if not len(data):
                            break
                        response += data
                    break
                except Exception as e:
                    # sys.stderr.write(str(e))
                    pass

        response = HttpResponse(response)
        sys.stderr.write(response.start_line)
        sys.stdout.write(response.message_body)

                # if not response_queue.empty():
        #     dns_response = response_queue.get()
        # ip = '0'
        # for answer in dns_response.answers:
        #     if len(answer)!=0:
        #         ip = answer[0]
        #         break
        #
        # if dns_response.get_qtype()==1:
        #     s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # else:
        #     s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        # s.settimeout(3)
        # s.connect((ip, port))
        # s.send(request)
        # try:
        #     response = ''
        #     while 1:
        #         data = s.recv(1024)
        #         if not len(data):
        #             break
        #         response += data
        # except Exception as e:
        #     sys.stderr.write(e)
        #     pass
        #
        # response = HttpResponse(response)
        #
        # sys.stderr.write(response.start_line)
        # sys.stdout.write(response.message_body)


if __name__ == "__main__":
    resolver = HttpResolver()
    argv = sys.argv
    resolver.get(argv[1])
