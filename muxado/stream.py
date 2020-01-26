import io, threading, queue

class Stream:
    def __init__(self, fsock, stid):
        self.fsock = fsock
        self.stid = stid
        self.inbuf = b''
        self.outbuf = b''
        self.window = 262144
        self.closed = False
        self.opened = False
    def onframe(self, frame):
        t, f, stid, data = frame
        assert stid == self.stid
        if t == 0: # rst
            if not self.closed:
                self.closed = True
                self.onupdate()
        elif t == 1: # data
            if self.closed:
                self.fsock.send((0, 0, self.stid, b'\0\0\0\0'))
            else:
                self.opened = True
                if f & 1:
                    self.closed = True
                self.inbuf += data
                if data:
                    self.fsock.send((2, 0, self.stid, len(data).to_bytes(4, 'big')))
                self.onupdate()
        elif t == 2: # wndinc
            self.window += int.from_bytes(data, 'big')
            self.send(b'')
        elif t == 3: # goaway
            if not self.closed:
                self.closed = True
                self.onerror()
    def recv(self, n=None):
        ans = self.inbuf[:n]
        self.inbuf = self.inbuf[len(ans):]
        return ans
    def send(self, data):
        if self.closed: raise BrokenPipeError()
        self.outbuf += data
        if self.outbuf and self.window:
            f = 0
            if not self.opened:
                f = 2
                self.opened = True
            data = self.outbuf[:self.window]
            self.outbuf = self.outbuf[self.window:]
            self.window -= len(data)
            self.fsock.send((1, f, self.stid, data))
    def close(self):
        self.closed = True
        self.fsock.send((1, 1, self.stid, b''))

class GenStream(Stream):
    def __init__(self, fsock, stid, gen):
        Stream.__init__(self, fsock, stid)
        self.gen = gen
        self.send(next(gen))
    def onupdate(self):
        data = self.recv()
        if not data and self.closed: data = None
        q = self.gen.send(data)
        if q == None: self.close()
        else: self.send(q)
    def onerror(self):
        self.gen.close()

class PiperStream(Stream):
    def __init__(self, fsock, stid, pipe):
        Stream.__init__(self, fsock, stid)
        self.pipe = pipe
        self.lock = threading.RLock()
    def onframe(self, frame):
        with self.lock: Stream.onframe(self, frame)
    def onupdate(self):
        data = self.recv()
        if not data and self.closed: data = None
        self.pipe.put(data)
    def send(self, data):
        with self.lock: Stream.send(self, data)
    def close(self):
        with self.lock: Stream.close(self)

class StreamIO(io.RawIOBase):
    def __init__(self, fsock, stid):
        self.pipe = queue.Queue()
        self.stream = PiperStream(fsock, stid, self.pipe)
        self.inbuf = b''
        self.lock = threading.Lock()
        self._closed = False
    def readinto(self, b):
        self._checkClosed()
        n = len(b)
        with self.lock:
            if not self.inbuf:
                ans = self.pipe.get()
                if ans == None:
                    self._closed = True
                else:
                    self.inbuf = ans
            if not self.closed:
                ans = self.inbuf[:n]
                self.inbuf = self.inbuf[n:]
            else:
                ans = b''
        b[:len(ans)] = ans
        return len(ans)
    def write(self, b):
        self._checkClosed()
        self.stream.send(b)
        return len(b)
    def close(self):
        self._checkClosed()
        self._closed = True
        self.stream.close()
    def onframe(self, frame):
        self.stream.onframe(frame)
    def readable(self):
        self._checkClosed()
        return True
    writable = readable
    def seekable(self):
        self._checkClosed()
        return False
