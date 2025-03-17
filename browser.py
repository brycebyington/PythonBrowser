import socket
import ssl

class URL:
    def __init__(self, url): 
        # __init__ is Python's syntax for class constructors
        # "self" is Python's analog for "this" in C++, which
        # is required to be the first parameter of any method
        
        # check the scheme
        # only handling data:text/html for now
        if url.startswith("data:text/html,"):
            # extract the data from the url
            self.scheme = "data"
            self.data = url.removeprefix("data:text/html,")
        else: 
            if url.startswith("view-source:"):
                self.scheme = "view-source"
                self.view_source = True
                url = url.removeprefix("view-source:")

            self.scheme, url = url.split("://", 1)
            assert self.scheme in ["http", "https", "file", "view-source"]
    
            self.host, url = url.split("/", 1)
            if self.scheme == "file":
                self.path = url
            else:
                self.path = '/' + url
            # split(s, n) splits a string at th e first n copies of s
            
            if self.scheme == "http":
                self.port = 80
            elif self.scheme == "https":
                self.port = 443

            # if url has port, parse and use as port instead
            if ":" in self.host and self.scheme != "file":
                self.host, port = self.host.split(":", 1)
                self.port = int(port)
            
    def request(self):
        
        if self.scheme == "file":
            file_object = open(self.path)
            return file_object.read()

        if self.scheme == "data":
            return "<html><head></head><body>{}</body></html>".format(self.data)
            
        # create a socket
        s = socket.socket(
            family = socket.AF_INET,
            type = socket.SOCK_STREAM,
            proto = socket.IPPROTO_TCP,
        )
        
        # connect to host on port 80 (http)
        # different address families take in different numbers
        # of arguments
        s.connect((self.host, self.port))
        
        # if https, wrap socket in ssl context
        if self.scheme == "https":
            ctx = ssl.create_default_context()
            s = ctx.wrap_socket(s, server_hostname=self.host)
    
        # make a request to the server
        request = "GET {} HTTP/1.1\r\n".format(self.path)
        request += "Host: {}\r\n".format(self.host)
        request += "Connection: close\r\n".format(self.host)
        request += "User-Agent: bryce-browser\r\n".format(self.host)
        request += "\r\n"
        # a blank newline is required at the end of a request
        # to end it and receive a response
        
        s.send(request.encode("utf8"))
        # encode converts text into bytes; "str" and "bytes" are unique
        # send returns the number of bytes sent to a server
        
        response = s.makefile("r", encoding="utf8", newline="\r\n")
        # makefile returns a file-like object containing every byte
        # receieved from the server
        # python turns the bytes into a string and accounts for HTTP's line ending
        
        # split the response into pieces
        statusline = response.readline()
        version, status, explanation = statusline.split(" ", 2)
        
        response_headers = {}
        while True:
            line = response.readline()
            if line == "\r\n": break
            header, value = line.split(":", 1)
            # split each line at the first colon and fill in a
            # map of header names -> header values
            response_headers[header.casefold()] = value.strip()
            # make all the headers lowercase
            # strip whitespace from values at beginning and end
        
        assert "transfer-encoding" not in response_headers
        assert "content-encoding" not in response_headers
        # make sure data is not sent unusually
        
        # if 300 level status, redirect
        if (status.startswith("3")):
            load(URL(response_headers["location"]))
        
        content = response.read()
        s.close()
        return content

def show(body, view_source):
        in_tag = False
        body_result = ""
        # iterate through request body, character by character
        # in_tag = currently between pair of brackets
        # not in_tag = current char is an angle bracket
        # normal characters not in a tag are printed
        
        if view_source == False:
            for c in body:
                if c == "<":
                    in_tag = True
                elif c == ">":
                    in_tag = False
                elif not in_tag:
                    # print(c, end="")
                    body_result += c
            
            # special characters (< and > literals)
            body_result = body_result.replace("&lt;", "<")
            body_result = body_result.replace("&gt;", ">")
            print(body_result)
        else:
            print(body)
                
def load(url):
    body = url.request()
    show(body, url.view_source)

if __name__ == "__main__":
    import sys
    load(URL(sys.argv[1]))
        
        