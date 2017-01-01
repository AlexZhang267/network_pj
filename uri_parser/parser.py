# coding = utf-8
import re
import sys


def parse_uri(uri):
    """
	:param uri:
	:return: [scheme, authority, path, query, fragment]
	"""
    try:
        pattern = re.compile("^(([^:/?#]+):)?(//([^/?#]*))?([^?#]*)(\?([^#]*))?(#(.*))?")
        match = re.match(pattern, uri).groups()
        if match[4]=='':
            return (match[1], match[3], "/", match[6], match[8])
        else:
            return (match[1], match[3], match[4], match[6], match[8])
    except Exception:
        sys.stderr.write("parse error")


if __name__ == '__main__':
    parse_uri("http://www.xiami.com")
