#!/usr/bin/env python3
"""
send_email.py
Builds and sends an HTML email with results and attaches logs.
"""
import argparse
import smtplib
from email.message import EmailMessage
from email.utils import formataddr
from pathlib import Path
import mimetypes
import os

TEMPLATES = Path('templates')
LOG_DIR = Path('logs')

def build_message(ticket, recipients, job_url, dry_run):
    status = 'SUCCESS'
    template = TEMPLATES / 'email_success.html'
    html = template.read_text()
    html = html.replace('{{TICKET}}', ticket)
    html = html.replace('{{JOB_URL}}', job_url)
    html = html.replace('{{DRY_RUN}}', str(dry_run))
    return html, status

def attach_logs(msg):
    for f in LOG_DIR.glob('*.log'):
        ctype, encoding = mimetypes.guess_type(str(f))
        ctype = ctype or 'application/octet-stream'
        maintype, subtype = ctype.split('/', 1)
        with open(f, 'rb') as fh:
            msg.add_attachment(fh.read(), maintype=maintype, subtype=subtype, filename=f.name)

def send(recipients, html, subject='Docker Promotion Results'):
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = formataddr(('DevOps Team', 'devops@example.com'))
    msg['To'] = recipients
    msg.set_content('This is an HTML email. If you see this, your client does not support HTML.')
    msg.add_alternative(html, subtype='html')
    attach_logs(msg)

    smtp_host = os.environ.get('SMTP_HOST', 'localhost')
    smtp_port = int(os.environ.get('SMTP_PORT', 25))
    smtp_user = os.environ.get('SMTP_USER')
    smtp_pass = os.environ.get('SMTP_PASS')
    use_tls = os.environ.get('SMTP_TLS', 'false').lower() == 'true'

    with smtplib.SMTP(smtp_host, smtp_port) as s:
        if use_tls:
            s.starttls()
        if smtp_user and smtp_pass:
            s.login(smtp_user, smtp_pass)
        s.send_message(msg)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--ticket', required=True)
    parser.add_argument('--recipients', default='')
    parser.add_argument('--dry-run', required=True)
    parser.add_argument('--job-url', default='')
    args = parser.parse_args()

    recipients = args.recipients or 'team@example.com'
    html, status = build_message(args.ticket, recipients, args.job_url, args.dry_run)
    send(recipients, html, f'Docker Promotion - {status} - {args.ticket}')

if __name__ == '__main__':
    main()
