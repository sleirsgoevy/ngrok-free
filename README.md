# ngrok-free

This is a free reimplementation of the ngrok v2 protocol. The information has been obtained by reverse-engineering the official client.

## Command-line client

```
usage: ngrok.py [--auth-token <auth_token>] <protocol> <port> [addr]

<protocol> can be one of `https`, `http`, `tls`, `tcp`.
<port> is the target port on your machine.
<addr> (optional) is the reserved remote address, if any.
```

## API

`ngrok.connect(auth_token="") -> ngrok.Ngrok`

Creates a new connection to ngrok. `auth_token` is an optional authentication token.

`Ngrok.bind_http(self, addr=None, proto="https") -> str`

Requests a tunnel, according to the protocol in `proto` (may be one of `https`, `http`, `tls`). `addr`, if supplied, must be a reserved hostname for the current user.

`Ngrok.bind_tcp(self, addr=None)`

Requests a TCP tunnel. `addr`, is supplied, must be a `(host, port)` tuple corresponding to a reserved TCP port for the current user.

Returns a `(host, port)` pair for the TCP port that has been bound to.

`Ngrok.accept(self)`

Waits for an incoming connection.

Returns a tuple `(sock, (host, port))`, where `sock` is a subclass of `io.RawIOBase` (NOT `socket.socket`), and `(host, port)` corresponds to the client's TCP port.
