#!/usr/bin/env python3

""" Port Check

Usage:
  port_check.py [--timeout=<timeout>] <host> <port>

Options:
  -h --help               Show this screen.
  -t --timeout=<timeout>  Controls number of seconds before the command will timeout. [default: 5]
  <host>                  Hostname or IP address.
  <port>                  Port number.
"""

import backoff
import socket
import sys

from docopt import docopt

def main():
    opts = docopt(__doc__)
    timeout = int(opts["--timeout"])
    host = opts["<host>"]
    port = int(opts["<port>"])

    if port_check(host, port, timeout):
        sys.exit(0)
    else:
        sys.exit(-1)


def port_check(host:str, port:int, timeout:int=300):
    @backoff.on_exception(backoff.expo,
                          ConnectionRefusedError,
                          max_time=timeout)
    def _check():
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, port))
        s.shutdown(2)
    
    try:
        _check()
    except ConnectionRefusedError:
        return False
    return True


if __name__ == '__main__':
    main()