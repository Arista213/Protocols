import argparse
import socket
import sys


class Args:
    def __init__(self):
        self.host, self.start, self.end, self.t, self.u = self._parse_args()

    @staticmethod
    def _parse_args():
        parser = argparse.ArgumentParser(
            description='TCP and UDP port scanner')
        parser.add_argument('--host', metavar='host', required=True,
                            default='localhost', help='host to scan')
        parser.add_argument('-p', '--ports', metavar='ports', required=True,
                            help='range of ports: 0-65535')
        parser.add_argument('-t', action='store_true',
                            help='To scan TCP ports')
        parser.add_argument('-u', action='store_true',
                            help='To scan UDP ports')
        args = parser.parse_args()
        max = 65535
        try:
            if '-' in args.ports:
                start, end = args.ports.split('-')
                start, end = int(start), int(end)
            else:
                start, end = int(args.ports), int(args.ports)
        except ValueError:
            print('Port number must be integer')
            sys.exit()
        if end > max:
            print('Port numbers must be less than 65535')
            sys.exit()
        if start > end:
            print('Invalid arguments')
            sys.exit()
        try:
            socket.gethostbyname(args.host)
        except socket.gaierror:
            print(f'Invalid host {args.host}')
            sys.exit()
        return args.host, start, end, args.t, args.u
