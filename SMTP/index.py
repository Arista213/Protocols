import random
import sys
import os
import argparse
import getpass
import time

import socket
import ssl
import urllib.request

import m_base64

ip = urllib.request.urlopen('https://api.ipify.org').read().decode('utf8')
context = ssl.create_default_context()

FILE_TYPES = {
    '.jpg': b'image/jpeg',
    '.jpeg': b'image/jpeg',
    '.png': b'image/png',
    '.gif': b'image/gif',
    '.tiff': b'image/tiff'
}


def auth():
    login = input('Enter login: ')
    password = getpass.getpass('Enter password: ')

    return login, password


def parse(args):
    parser = argparse.ArgumentParser(description="SMTP Client that send images from directory to mail")

    parser.add_argument('--ssl', action='store_true', help='Enable ssl connection, if server allows it')
    parser.add_argument('-s', '--server', action='store', required=True, help='Mail server in format '
                                                                              'server_host[:port]')
    parser.add_argument('-t', '--to', action='store', dest='receiver', required=True, help='Receiver email')
    parser.add_argument('-f', '--from', action='store', dest='sender', default='<>',
                        help='Sender email. By default is <>')
    parser.add_argument('--subject', action='store', default='', help='Set email subject')
    parser.add_argument('--auth', action='store_true', help='Require authorization')
    parser.add_argument('-v', '--verbose', action='store_true', help='Show log')
    parser.add_argument('-d', '--directory', action='store', default='.', help='Directory with pictures to send')

    return parser.parse_args(args)


def data_packer(dir_to_images) -> bytes:
    boundary = str(time.time())
    result = [f'Content-Type: multipart/mixed; boundary="{boundary}"\r\n\r\n'.encode('utf8')]
    if not os.path.exists(dir_to_images) or not os.path.isdir(dir_to_images):
        print('Directory is not exists')
        exit(2)

    images = next(os.walk(dir_to_images))[2]
    boundary = boundary.encode('utf8')
    counter = 0
    for image in images:
        ext = os.path.splitext(image)[1]
        encode_img = image.encode('utf8')
        if ext in FILE_TYPES:
            counter += 1
            result.extend([b'--', boundary, b'\r\n', b'Content-Disposition: attachment; filename="',
                           encode_img, b'"\r\nContent-Transfer-Encoding: base64\r\nContent-Type: ',
                           FILE_TYPES[ext], b'; name="', encode_img, b'"\r\n\r\n'])
            with open(os.path.join(dir_to_images, image), 'rb') as f:
                data = m_base64.encode(f.read())
                for i in range(0, len(data), 76):
                    result.extend([data[i: i + 76], b'\n'])

    result.extend([b'--', boundary, b'--'])

    print(f'Read {counter} images')

    return b''.join(result)


class Server:
    def __init__(self, host, port, sender, receiver, message_body, subject, secure=False, auth=False,
                 verbose=False, timeout=2):
        self.host = host
        self.port = port
        self.sender = sender
        self.receiver = receiver
        self.auth = auth
        self.parse_auth = False
        self.verbose = verbose
        self.ssl = secure
        self.message = [message_body]
        self.subject = f'=?UTF-8?B?{m_base64.encode(subject.encode("utf8")).decode("utf8")}?='

        self.pipelining = False
        self.size = -1

        socket.setdefaulttimeout(timeout)
        self._sock = None
        self._additional = None

        self.header = (f"From: {self.sender}\r\nTo: {self.receiver}\r\nSubject: {self.subject}\r\n"
                       "MIME-Version: 1.0".encode('utf8'))

    def _connect(self):
        try:
            self._sock = socket.create_connection((self.host, self.port))
        except socket.timeout:
            print(f'Can not connect to the server {self.host}:{self.port}')
            exit(0)

        if self.ssl:
            self._additional = self._sock
            try:
                self._sock = context.wrap_socket(self._sock, server_hostname=self.host)
            except ssl.SSLError:
                print('Can not establish secure connection using SSL Wrapper.')
                self._sock = socket.create_connection((self.host, self.port))

    def _start_tls(self):
        self._send('STARTTLS')
        if b'220' in self._receive():
            try:
                self._sock = context.wrap_socket(self._sock, server_hostname=self.host)
            except ssl.SSLError:
                print('Can not establish secure connection using START TLS. Exit')
                exit(0)

    def start(self):
        self._connect()
        # Приветствие сервера
        self._receive()

        # Привет серверу и парсинг прищедших настроек
        self._send(f'EHLO {ip}')
        self._parse_abilities(self._receive())

        # Если подключение было не к порту SMTPS, и сервер поддеривает STARTTLS то подключаем его
        if self.ssl:
            self._start_tls()

        # Здесь по-новой приветствуем сервер
        self._send(f'EHLO {ip}')
        self._parse_abilities(self._receive())

        # Если требуется аутентификация и ее поддерживает сервер, просим пользователя логин и пароль
        if self.parse_auth:
            self._auth()

        self._split_message()
        for mess in self.message:
            self._mail(mess)
        print('Message has been sent')

    def _receive(self, use_try=True):
        if use_try:
            try:
                data = self._sock.recv(65536)
            except socket.error:
                print('Connection closed by server')
                self.close()
                exit(0)
            else:
                if self.verbose:
                    print(f'S: {data.decode("utf8")}')
                return data
        data = self._sock.recv(65536)
        if self.verbose:
            print(f'S: {data.decode("utf8")}')
        return data

    def _send(self, data, add_verbose=True):
        if isinstance(data, str):
            data = data.encode('utf8')
        if data[len(data) - 3:] != b'\r\n':
            data += b'\r\n'
        try:
            self._sock.send(data)
        except ConnectionAbortedError:
            print('Connection reset by server')
        if self.verbose and add_verbose:
            print('C:', data.decode('utf8', errors='ignore'))

    def _parse_abilities(self, data):
        self.parse_auth = self.auth and (b'AUTH' in data)
        self.ssl = self.ssl and (b'STARTTLS' in data)
        self.pipelining = b'PIPELINING' in data
        data_split = data.split(b'\r\n')
        if self.parse_auth:
            authorization = list(filter(lambda x: b'AUTH' in x, data_split))[0]
            self.auth_types = authorization.split()[1:]
        if b'SIZE' in data:
            self.size = int(next(filter(lambda x: b'SIZE' in x, data_split)).split()[-1])

    def _auth(self):
        func = lambda log, pas: b'AUTH PLAIN ' + m_base64.encode(f'\0{log}\0{pas}')

        while True:
            login, password = auth()
            self._send(func(login, password), add_verbose=False)
            data = self._receive()
            if b'235' in data:
                break

    def _mail(self, data):
        if self.pipelining:
            self._send(f'MAIL FROM: <{self.sender}>\r\nRCPT TO: <{self.receiver}>\r\nDATA')
            while True:
                try:
                    self._receive(False)
                except socket.timeout:
                    break
            self._send(self.header, False)
            self._send(data, False)
            self._send('.', False)
            while True:
                try:
                    self._receive(False)
                except socket.timeout:
                    return

        self._send(f'MAIL FROM: {self.sender}')
        data_ = self._receive()
        if not data_.startswith(b'2'):
            print(f"Can not sent message. Last message:\n{data_.decode('utf8')}")
            self.close()
            exit(0)
        self._send(f'RCPT TO: <{self.receiver}>')
        self._receive()
        self._send('DATA')
        self._receive()
        self._send(f'From: {self.sender}\r\nTo: {self.receiver}\r\nSubject: {self.subject}', False)
        self._send(data, False)
        self._send('\r\n.\r\n', False)
        self._receive()

    def _split_message(self):
        if self.size == -1 or len(self.message[0]) + len(self.header) < self.size:
            return

        mess = self.message[0]
        self.message = []
        size = self.size - len(self.header) - 100
        message_count = len(mess) // size
        if len(mess) % self.size > 0:
            message_count += 1
        random_id = random.randint(0, 2 ** 16)
        for i in range(0, len(mess), size):
            temp_mess = [b'Content-Type: message/partial; ',
                         f'id="{random_id}"; number={i // self.size + 1}; total={message_count}\r\n\r\n'.encode('utf8'),
                         mess[i:i + self.size]]
            self.message.append(b''.join(temp_mess))

    def close(self):
        if self._sock:
            self._sock.close()
        if self._additional:
            self._additional.close()


def main(args):
    args = parse(args[1:])
    data = data_packer(args.directory)
    port = 25
    if ':' in args.server:
        port = args.server.split(':')[1]
        args.server = args.server.split(':')[0]
    server = Server(args.server, port, args.sender, args.receiver, data, args.subject, secure=args.ssl, auth=args.auth,
                    verbose=args.verbose)
    try:
        server.start()
    finally:
        server.close()


if __name__ == "__main__":
    main(sys.argv)
