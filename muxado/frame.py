class FramedSocket:
    def __init__(self, sock):
        self.sock = sock
    def recv_frame(self):
        header = self.sock.recv(8)
        if not header: return None
        while len(header) < 8: header += self.sock.recv(8 - len(header))
        l = int.from_bytes(header[:3], 'big')
        t = header[3] >> 4
        f = header[3] & 15
        assert t < 4 and f < 4
        stid = int.from_bytes(header[4:], 'big')
        data = b''
        while len(data) < l: data += self.sock.recv(l - len(data))
        return (t, f, stid, data)
    def send_frame(self, frame):
        t, f, stid, data = frame
        self.sock.sendall(len(data).to_bytes(3, 'big')+bytes((t<<4|f,))+stid.to_bytes(4, 'big')+data)
    send = send_frame
    def onframe(self, frame):
        ...
    def mainloop(self):
        while True: self.onframe(self.recv_frame())
