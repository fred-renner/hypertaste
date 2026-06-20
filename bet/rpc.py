"""The wire between the agent's confined client and the world server.

Newline-delimited JSON over a Unix-domain socket. One request, one response,
per connection. Deliberately tiny: this is the *only* channel between the agent
and the world, so it is easy to read top-to-bottom and audit for leaks.
"""

import json
import socket


def call(sock_path: str, req: dict, timeout: float = 30.0) -> dict:
    """Send one request, return one response dict. Raises on transport error."""
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect(sock_path)
        s.sendall((json.dumps(req) + "\n").encode("utf-8"))
        buf = b""
        while not buf.endswith(b"\n"):
            chunk = s.recv(65536)
            if not chunk:
                break
            buf += chunk
        return json.loads(buf.decode("utf-8").strip())
    finally:
        s.close()
