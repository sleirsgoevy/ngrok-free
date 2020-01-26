import queue, threading
from .frame import FramedSocket
from .stream import StreamIO

class Listener(FramedSocket):
    def __init__(self, sock, conn_start, conn_type, *conn_args):
        FramedSocket.__init__(self, sock)
        self.conn_start = conn_start
        self.conns = {}
        self.conn_type = conn_type
        self.conn_args = conn_args
    def onframe(self, frame):
        if frame[:3] == (3, 0, 0): return
        t, f, stid, data = frame
        new = False
        if stid not in self.conns:
            assert f & 2
            self.conns[stid] = self.conn_type(self, stid, *self.conn_args)
            new = True
        self.conns[stid].onframe(frame)
        if new: self.onaccept(self.conns[stid])
    def open(self, conn_type = None, *conn_args):
        stid = self.conn_start
        self.conn_start += 2
        if conn_type == None:
            conn_type = self.conn_type
            conn_args = self.conn_args
        self.conns[stid] = conn_type(self, stid, *conn_args)
        return self.conns[stid]
    def onaccept(self, sock):
        ...

class ThreadedListener(Listener):
    def __init__(self, *args, **kwds):
        Listener.__init__(self, *args, **kwds)
        self.lock = threading.Lock()
        self.accept_q = queue.Queue()
        threading.Thread(target=self.mainloop, daemon=True).start()
    def open(self, *args, **kwds):
        with self.lock:
            return Listener.open(self, *args, **kwds)
    def onframe(self, frame):
        with self.lock:
            Listener.onframe(self, frame)
    def onaccept(self, sock):
        self.accept_q.put(sock)
    def accept(self):
        return self.accept_q.get()

def create_listener(sock):
    return ThreadedListener(sock, 3, StreamIO)
