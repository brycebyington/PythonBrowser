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
        #self.width = WIDTH
        #self.height = HEIGHT
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
        self.canvas.pack()
        #self.canvas.bind("<Configure>", self.resize)
        # distance scrolled
        self.scroll = 0
        self.display_list = []
        # bind scroll function to down key
        # self.scrolldown is an event handler
        self.window.bind("<Down>", self.scrolldown)
        self.window.bind("<Up>", self.scrollup)
        self.window.bind("<MouseWheel>", self.mousescroll)
    
    #def resize(self, e):
        # event contains window information
        # and updates when the window is resized
        #self.width = e.width
        #self.height = e.height
        # have to update the display list before re-drawing
        #self.display_list = Layout(self.tokens).display_list
        #self.draw()
        
    
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
        for x, y, word, font in self.display_list:
            # skip drawing characters that are off screen (continue)
            if y > self.scroll + HEIGHT: continue
            # skip characters below viewport
            if y + font.metrics("linespace") < self.scroll: continue
            # if x, y are the last elements in the display_list, prevent further scrolling
            # check if current cursor position is equal to the last element in display_list
            # if it is, set self.scroll to the y value of the last element in display_list - height
            #if (x, y) == (self.display_list[-1][0], self.display_list[-1][1]):
            #   self.scroll = self.display_list[-1][1] - HEIGHT
                
            # when self.scroll changes value, the page scrolls
            self.canvas.create_text(x, y - self.scroll, text=word, font=font, anchor="nw")

    def load(self, url):
        body = url.request()
        tokens = lex(body)
        self.display_list = Layout(tokens).display_list
        self.draw()
class URL:
    def __init__(self, url):

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

def lex(body):
    out = []
    # stores either text or tag contents before they can be used
    buffer = ""
    in_tag = False
    # iterate through request body, character by character
    # in_tag = currently between pair of brackets
    # not in_tag = current char is an angle bracket
    # normal characters not in a tag are printed
    
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
            buffer += c
     # check if buffered text
    if not in_tag and buffer:
        out.append(Text(buffer))
    return out

# cache to re-use font objects when possible
# instead of creating new ones
FONTS = {}
# keys: (size, weight, style)
# values: (font object)
def get_font(size, weight, style):
    key = (size, weight, style)
    if key not in FONTS:
        font = tkinter.font.Font(size=size, weight=weight,
            slant=style)
        label = tkinter.Label(font=font)
        FONTS[key] = (font, label)
    return FONTS[key][0]

class Layout:
    def __init__(self, tokens):
        self.tokens = tokens
        self.display_list = []

        self.cursor_x = HSTEP
        self.cursor_y = VSTEP
        self.weight = "normal"
        self.style = "roman"
        self.size = 12

        self.line = []
        for tok in tokens:
            self.token(tok)
        self.flush()

    def token(self, tok):
        if isinstance(tok, Text):
            for word in tok.text.split():
                self.word(word)
        elif tok.tag == "i":
            self.style = "italic"
        elif tok.tag == "/i":
            self.style = "roman"
        elif tok.tag == "b":
            self.weight = "bold"
        elif tok.tag == "/b":
            self.weight = "normal"
        elif tok.tag == "small":
            self.size -= 2
        elif tok.tag == "/small":
            self.size += 2
        elif tok.tag == "big":
            self.size += 4
        elif tok.tag == "/big":
            self.size -= 4
        elif tok.tag == "br":
            self.flush()
        elif tok.tag == "/p":
            self.flush()
            self.cursor_y += VSTEP
        
    def word(self, word):
        font = get_font(self.size, self.weight, self.style)
        w = font.measure(word)
        if self.cursor_x + w > WIDTH - HSTEP:
            self.flush()
        self.line.append((self.cursor_x, word, font))
        self.cursor_x += w + font.measure(" ")

    # flush does three things:
    # align the words along the baseline
    # add the words to the display list
    # update cursor x and y positions
    def flush(self):
        if not self.line: return
        # compute where "on the line" is for each word
        metrics = [font.metrics() for x, word, font in self.line]
        max_ascent = max([metric["ascent"] for metric in metrics])
        # + 1.25 accounts for leading
        baseline = self.cursor_y + 1.25 * max_ascent
        for x, word, font in self.line:
            # y starts at baseline and moves up 
            # by just enough to accomodate word's ascent
            y = baseline - font.metrics("ascent")
            self.display_list.append((x, y, word, font))
        max_descent = max([metric["descent"] for metric in metrics])
        # cursor y position moves far enough down below baseline
        # to account for the deepest descender
        self.cursor_y = baseline + 1.25 * max_descent
        # update cursor x position and line fields
        self.cursor_x = HSTEP
        self.line = []



if __name__ == "__main__":
    import sys
    Browser().load(URL(sys.argv[1]))
    # tk mainloop asks the desktop environment for recent inputs,
    # calls application to update state, then redraws the window
    tkinter.mainloop()
        