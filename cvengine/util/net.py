from collections import defaultdict
import socket

_ports = defaultdict(dict)


def net_check(port, addr=None, force=False):
    """Checks the availablility of a port"""
    port = int(port)
    # REM
    # if not addr:
    #     addr = urlparse.urlparse(store.base_url).hostname
    if port not in _ports[addr] or force:
        # First try DNS resolution
        try:
            addr = socket.gethostbyname(addr)

            # Then try to connect to the port
            try:
                socket.create_connection((addr, port), timeout=10)
                _ports[addr][port] = True
            except socket.error:
                _ports[addr][port] = False
        except Exception:
            _ports[addr][port] = False
    return _ports[addr][port]
