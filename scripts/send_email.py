#!/usr/bin/env python3
# send_email.py - compose HTML email (success/failure) and send via local sendmail or SMTP


import argparse
import smtplib
from email.message import EmailMessage
from pathlib import Path


parser = argparse.ArgumentParser()
parser.add_argument('--ticket', default='')
parser.add_argument('--recipients', default='')
parser.add_argument('--log', default='/var/log/jenkins/docker_tagging.log')
parser.add_argument('--status', choices=['SUCCESS','FAILURE'], default='SUCCESS')
parser.add_argument('--dry-run', choices=['YES','NO'], default='NO')
args = parser.parse_args()


TPL_DIR = Path(__file__).resolve().parent.parent / 'templates'


def load_template(status):
fname = 'email_success.html' if status == 'SUCCESS' else 'email_failure.html'
return (TPL_DIR / fname).read_text()




def send_email(body_html, subject, attachments, recipients):
msg = EmailMessage()
msg['Subject'] = subject
msg['From'] = 'ci@example.com'
msg['To'] = recipients
msg.set_content('This is an HTML email. Please view in an HTML capable client.')
msg.add_alternative(body_html, subtype='html')


for att in attachments:
with open(att, 'rb') as f:
data = f.read()
msg.add_attachment(data, maintype='text', subtype='plain', filename=Path(att).name)


# Simple send via localhost
with smtplib.SMTP('localhost') as s:
s.send_message(msg)




if __name__ == '__main__':
recipients = args.recipients.split(',') if args.recipients else ['team@example.com']
html = load_template(args.status)
# simple subject with ticket link
subject = f"[CI] Docker Tagging {args.status} - {args.ticket}"
attachments = [args.log] if Path(args.log).exists() else []
send_email(html, subject, attachments, ','.join(recipients))