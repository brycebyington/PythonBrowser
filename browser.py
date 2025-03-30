import socket
import ssl
import tkinter
import tkinter.font

# to-dos:
# - http compression
# - caching
# - keep-alive
# - OpenMoji support
# - scrollbar
# - alternate text direction
# - macOS touchpad scrolling

WIDTH, HEIGHT = 800, 600
HSTEP, VSTEP = 13, 18
# HSTEP: space between characters, VSTEP: space between lines
SCROLL_STEP = 100
LINEBREAK = VSTEP * 3
# how much to scroll

# characters outside a tag
# lex avoids empty Text objects
class Text:
    def __init__(self, text):
        self.text = text
# contents of a tag
class Tag:
    def __init__(self, tag):
        self.tag = tag

class Browser:
    def __init__(self):
        # create the window
        self.window = tkinter.Tk()
        self.width = WIDTH
        self.height = HEIGHT
        # create the canvas inside the window
        # window is passed as an argument to inform
        # tk of where to display the canvas
        self.canvas = tkinter.Canvas(
            self.window,
            width=WIDTH,
            height=HEIGHT
        )
        # position the canvas inside the window
        # fill="both": fill entire space with widget
        # expand=1: expand to fill any space not otherwise used
        self.canvas.pack(fill="both", expand=1)
        self.canvas.bind("<Configure>", self.resize)
        # distance scrolled
        self.scroll = 0
        # bind scroll function to down key
        # self.scrolldown is an event handler
        self.window.bind("<Down>", self.scrolldown)
        self.window.bind("<Up>", self.scrollup)
        self.window.bind("<MouseWheel>", self.mousescroll)
    
    def resize(self, e):
        # event contains window information
        # and updates when the window is resized
        self.width = e.width
        self.height = e.height
        # have to update the display list before re-drawing
        self.display_list = Layout(self.tokens,  self.width).display_list
        self.draw()
        
    
    def scrolldown(self, e):
        # e is an event argument, which is ignored here because
        # key presses only require information about
        # whether or not the key is pressed
        self.scroll += SCROLL_STEP
        self.draw()
    
    def scrollup(self, e):
        # negative number to scroll up because vertical coordinates are backwards
        self.scroll -= SCROLL_STEP
        self.draw()
    
    def mousescroll(self, e):
        # e.delta: how far and in what direction to scroll
        self.scroll -= e.delta
        self.draw()
    

    def draw(self):
        # erase old text before drawing new text when scrolling down
        self.canvas.delete("all")
        # loop through the display list and draw each character
        # draw is included in Browser since it needs access to the canvas
        for x, y, c, font in self.display_list:
            # skip drawing characters that are off screen (continue)
            if y > self.scroll + self.height: continue
            # skip characters below viewport
            if y + VSTEP < self.scroll: continue
            # y + VSTEP: bottom edge of the character

            # if x, y are the last elements in the display_list, prevent further scrolling
            # check if current cursor position is equal to the last element in display_list
            # if it is, set self.scroll to the y value of the last element in display_list - height
            if (x, y) == (self.display_list[-1][0], self.display_list[-1][1]):
                self.scroll = self.display_list[-1][1] - self.height
                
            # when self.scroll changes value, the page scrolls
            self.canvas.create_text(x, y - self.scroll, text=c, font=font)

    def load(self, url):
        body = url.request()
        self.tokens = lex(body, url.view_source)
        self.display_list = Layout(self.tokens,  self.width).display_list
        self.draw()
class URL:
    def __init__(self, url):
        # default view_source to false
        self.view_source = False

        # __init__ is Python's syntax for class constructors
        # "self" is Python's analog for "this" in C++, which
        # is required to be the first parameter of any method
        
        if url == "about:blank":
            # render blank page
            self.scheme = "about"
            self.host = "blank"
            return
        
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

            try:
                self.scheme, url = url.split("://", 1)
            except:
                self.scheme = "about"
                self.host = "blank"
                return
            
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
        
        if self.scheme == "about" and self.host == "blank":
            return "<html><head></head><body></body></html>"
            
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
        if status.startswith("3"):
            Browser().load(URL(response_headers["location"]))
        
        content = response.read()
        s.close()
        return content

def lex(body, view_source):
    out = []
    # stores either text or tag contents before they can be used
    buffer = ""
    in_tag = False
    # iterate through request body, character by character
    # in_tag = currently between pair of brackets
    # not in_tag = current char is an angle bracket
    # normal characters not in a tag are printed
    
    if view_source == False:
        for c in body:
            if c == "<":
                in_tag = True
                if buffer: out.append(Text(buffer))
                buffer = ""
            elif c == ">":
                in_tag = False
                out.append(Tag(buffer))
                buffer = ""
            else:
                # special characters (< and > literals)
                if c == "&lt;":
                    buffer += "<"
                elif c == "&gt;":
                    buffer += ">"
                else:
                    buffer += c
            # check if buffered text
        if not in_tag and buffer:
            out.append(Text(buffer))
        return out
        
    # if view_source is True print source code
    else:
        return body
    
class Layout:
    def __init__(self, tokens, width):
        self.display_list = []
        self.cursor_x = HSTEP
        self.cursor_y = VSTEP
        self.weight = "normal"
        self.style = "roman"
        self.width = width
        
        for tok in tokens:
            self.token(tok)
    
    def word(self, word):
        # initialize font
        font = tkinter.font.Font(
            size=16,
            weight=self.weight,
            slant=self.style,
        )
        w = font.measure(word)
        self.display_list.append((self.cursor_x, self.cursor_y, word, font))
        # incremeent x position by width of word + space
        # this is necessary since split removes whitespace
        self.cursor_x += w + font.measure(" ")
        self.cursor_x += HSTEP
        # shift right after each character
        if self.cursor_x + w > self.width - HSTEP:
            # multiply linespace by 1.25 to add space between lines
            self.cursor_y += font.metrics("linespace") * 1.25
            # if x position is >= the screen width minus a step,
            # reset x position and increment y position to
            # go to a new line
            if (word == "\n"):
                #
                self.cursor_y += LINEBREAK
            else:    
                self.cursor_y += VSTEP
            self.cursor_x = HSTEP
        
    def token(self, tok):
        if isinstance(tok, Text):
            for word in tok.text.split():
                self.word(word)
        # support for weights and styles
        # this supports nested tags as well
        elif tok.tag == "i":
            self.style = "italic"
        elif tok.tag == "/i":
            self.style = "roman"
        elif tok.tag == "b":
            self.weight = "bold"
        elif tok.tag == "/b":
            self.weight = "normal"


if __name__ == "__main__":
    import sys
    Browser().load(URL(sys.argv[1]))
    # tk mainloop asks the desktop environment for recent inputs,
    # calls application to update state, then redraws the window
    tkinter.mainloop()
        