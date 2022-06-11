#!/usr/bin/env python3

""" Listener check

Usage:
  port_check.py <bindip> <port>

Options:
  -h --help               Show this screen.
  <bindip>                Bind IP address.
  <port>                  Port number.
"""

import re
import sys

from docopt import docopt


def main():
    opts = docopt(__doc__)
    bindip = opts["<bindip>"]
    port = opts["<port>"]

    with open('/proc/net/tcp') as f:
        sockets = read_tcp_proc(f.read())

    for info in sockets:
        info = info.rstrip()
        row = re.split(r'\s+', info)
        (localhost, localport) = host_port(row[1])
        (remotehost, remoteport) = host_port(row[2])
        if not (remotehost == '0.0.0.0' and remoteport == '0'):
            continue

        if localhost == bindip and localport == port:
            sys.exit(0)

    sys.exit(-1)


def read_tcp_proc(procnet):
    sockets = procnet.split('\n')[1:-1]
    return [line.strip() for line in sockets]


def split_every_n(data, n):
    return [data[i:i+n] for i in range(0, len(data), n)]


def host_port(address):
    hex_addr, hex_port = address.split(':')
    addr_list = split_every_n(hex_addr, 2)
    addr_list.reverse()
    addr = ".".join(map(lambda x: str(int(x, 16)), addr_list))
    port = str(int(hex_port, 16))
    return (addr, port)


if __name__ == '__main__':
    main()
