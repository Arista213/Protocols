import email.parser
import imaplib
import itertools
import re
import sys
from email.header import decode_header
from email.message import Message
from getpass import getpass
from typing import Tuple, Callable, Any

import typer


def get_header(header: str, message: Message) -> str:
    header, encoding = decode_header(message[header])[0]
    if isinstance(header, bytes) and not encoding == 'unknown-8bit':
        header = header.decode(encoding='UTF-8' if (encoding is None) else encoding)
    return header


def count_attachments(message: Message) -> int:
    count: int = 0
    for part in message.walk():
        if part.get_content_maintype() == 'multipart' or part.get('Content-Disposition') is None:
            continue
        count += 1
    return count


def fetch_emails(mail_connection, email_type="ALL"):
    status, response = mail_connection.search(None, '({})'.format(email_type))

    if 'OK' in status:
        emails_ids = response[0].decode().split()
        if emails_ids:
            for email_id in emails_ids:
                fetch_status, data = mail_connection.fetch(email_id, '(RFC822)')
                if 'OK' in fetch_status:
                    message: Message = email.parser.BytesParser().parsebytes(data[0][1])

                    if message.is_multipart():
                        mail_content = ''

                        for part in message.get_payload():
                            if part.get_content_type() == 'text/plain':
                                mail_content += part.get_payload()
                    else:
                        mail_content = message.get_payload()

                    mail_from = get_header('from', message)
                    mail_subject = get_header('subject', message)
                    mail_date = get_header('date', message)
                    mail_size = len(mail_content)
                    mail_attachments_count = count_attachments(message)

                    yield {
                        'From': mail_from,
                        'Subject': mail_subject,
                        'Date': mail_date,
                        'Size': str(mail_size),
                        "Count of attachments": str(mail_attachments_count)
                    }


def get_emails(mail_connection):
    _, mailboxes = mail_connection.list()
    for mailbox_in_bytes in mailboxes:
        if isinstance(mailbox_in_bytes, bytes):
            pattern = R"INBOX/\w+|INBOX"
            regex = re.search(pattern, mailbox_in_bytes.decode())
            if regex:
                mailbox = regex.group(0)
                status, _ = mail_connection.select(mailbox)

                if status == 'OK':
                    for email_data in fetch_emails(mail_connection):
                        yield email_data


def login(mail, user, password) -> bool:
    try:
        mail.login(user, password)
        print("Login success!")
        return True
    except imaplib.IMAP4.error | imaplib.IMAP4_SSL.error:
        print("Login failed!")
    return False


def main(
        server: str = typer.Option(..., '-s', '--server', help='imap server to connect'),
        user_email: str = typer.Option(..., '-u', '--user', help='user email'),
        emails_range: Tuple[int, int] = typer.Option((None, None), '-n', help='emails range', show_default=False),
        ssl: bool = False
):
    start, end = emails_range
    if start is None:
        start = 0
    if end is None:
        end = sys.maxsize

    host, *port = server.split(':')

    if ssl:
        port = 993 if len(port) == 0 else port.pop()  # If user didn't write port with ssl. Default: 993
    else:
        port = 143 if len(port) == 0 else port.pop()  # If user didn't write port without ssl. Default: 143

    mail_connection = imaplib.IMAP4(host, port) if not ssl else imaplib.IMAP4_SSL(host, port)

    print("Logging into mailbox...")

    password = getpass()
    if login(mail_connection, user_email, password):
        print("Fetching emails...")
        emails = get_emails(mail_connection)

        for _ in range(0, start):
            emails.__next__()

        mail_separator = '-' * 100

        if emails:
            for email_data in itertools.islice(emails, end - start):
                print(mail_separator)
                for key in email_data:
                    print(f'{key}: {email_data[key]}')
                print(mail_separator)

        mail_connection.close()
        mail_connection.logout()
        print("Logout of mailbox...")


def run(function: Callable[..., Any], add_completion: bool = False) -> Any:
    app = typer.Typer(add_completion=add_completion)
    app.command()(function)
    app()


if __name__ == '__main__':
    run(main)
