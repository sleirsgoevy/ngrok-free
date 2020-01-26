import muxado.listen, muxado.stream, threading, json, io, ssl, socket, sys

class NgrokListener(muxado.listen.ThreadedListener):
    def __init__(self, sock, authtoken=''):
        muxado.listen.ThreadedListener.__init__(self, sock, 3, muxado.stream.StreamIO)
        auth = self.open()
        auth.write(b'\0\0\0\0')
        auth.write((json.dumps({"Version":["2"],"ClientId":"","Extra":{"OS":"linux","Arch":"amd64","Authtoken":authtoken,"Version":"2.2.8","Hostname":"tunnel.us.ngrok.com","UserAgent":"ngrok/2","Metadata":"","Cookie":""}})+'\n').encode('utf-8'))
        b = io.BufferedReader(auth, 1)
        ans = json.loads(b.readline().decode('utf-8'))
        assert ans['Version'] == '2'
    def _bind(self, opts, proto):
        sock = self.open()
        sock.write(b'\0\0\0\1')
        sock.write((json.dumps({"Id":"","Proto":proto,"Opts":opts,"Extra":{"Balance":False,"Token":""}})+'\n').encode('utf-8'))
        b = io.BufferedReader(sock, 1)
        ans = json.loads(b.readline().decode('ascii'))
        if ans['Error']: raise PermissionError(ans['Error'])
        return ans['URL']
    def bind_http(self, hostname=None, proto='https'):
        return self._bind({"Hostname":hostname or '',"Auth":"","Subdomain":""}, proto)
    def bind_tcp(self, remote_addr=None):
        addr = self._bind({"Addr": '%s:%d'%remote_addr if remote_addr else ''}, 'tcp')
        assert addr.startswith('tcp://')
        h, p = addr[6:].rsplit(':', 1)
        if h == '[%s]'%h[1:-1]: h = h[1:-1]
        return (h, int(p))
    @staticmethod
    def _heartbeat_thread(sock):
        while True: sock.write(sock.read(4))
    def _onaccept_thread(self, sock):
        kind = sock.read(4)
        assert len(kind) == 4
        if kind == b'\xff\xff\xff\xff':
            self._heartbeat_thread(sock)
        elif kind == b'\x00\x00\x00\x03':
            l = sock.read(8)
            assert len(l) == 8
            l = int.from_bytes(l, 'little')
            d = b''
            while len(d) != l: d += sock.read(l - len(d))
            d = json.loads(d.decode('ascii'))
            h, p = d['ClientAddr'].rsplit(':', 1)
            if h == '[%s]'%h[1:-1]: h = h[1:-1]
            p = int(p)
            self.accept_q.put((sock, (h, p)))
        else: sock.close()
    def onaccept(self, sock):
        threading.Thread(target=self._onaccept_thread, args=(sock,), daemon=True).start()

def connect(authtoken=''):
    return NgrokListener(ssl.wrap_socket(socket.create_connection(('tunnel.us.ngrok.com', 443))), authtoken)

def main(*args):
    args = list(args)
    def usage(): 
        print("""\
usage: ngrok.py [--auth-token <auth_token>] <protocol> <port> [addr]

<protocol> can be one of `https`, `http`, `tls`, `tcp`.
<port> is the target port on your machine.
<addr> (optional) is the reserved remote address, if any.""", file=sys.stderr)
        exit(1)
    authtoken = None
    if '--auth-token' in args:
        i = args.index('--auth-token')
        if i == len(args) - 1:
            usage()
        authtoken = args[i+1]
        del args[i:i+2]
    if len(args) == 2:
        proto, port = args
        addr = ''
    elif len(args) == 3:
        proto, port, addr = args
    else:
        usage()
    port = int(port)
    if proto in ('http', 'https', 'tls'):
        self = connect(authtoken) if authtoken != None else connect()
        print('listening on', self.bind_http(addr, proto))
    elif proto == 'tcp':
        self = connect(authtoken) if authtoken != None else connect()
        print('listening on %s:%d'%self.bind_tcp(addr))
    else:
        usage()
    def copy_thread(sock1, sock2):
        while True:
            buf = sock1.read(4096)
            sock2.write(buf)
            if buf == b'': sock2.close()
    while True:
        conn, remote_addr = self.accept()
        print('new connection from %s:%d'%(remote_addr))
        try: conn2s = socket.create_connection(('0.0.0.0', port))
        except socket.error:
            print('connection to :%d failed'%port)
            continue
        conn2 = conn2s.makefile('rwb', 0)
        conn2.close = conn2s.close
        threading.Thread(target=copy_thread, args=(conn, conn2), daemon=True).start()
        threading.Thread(target=copy_thread, args=(conn2, conn), daemon=True).start()

if __name__ == '__main__':
    main(*sys.argv[1:])
