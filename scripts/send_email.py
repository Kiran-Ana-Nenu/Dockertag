#!/usr/bin/env python3
import smtplib, argparse, os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.application import MIMEApplication

parser = argparse.ArgumentParser()
parser.add_argument('--ticket', required=True)
parser.add_argument('--recipients', required=True)
parser.add_argument('--log', required=True)
parser.add_argument('--status', choices=['SUCCESS','FAILURE'], required=True)
args = parser.parse_args()

def send_email():
    with open(args.log, 'r') as f:
        log_content = f.read()

    msg = MIMEMultipart('mixed')
    msg['Subject'] = f"Release Notification - {args.ticket} - {args.status}"
    msg['From'] = "devops@company.com"
    msg['To'] = args.recipients

    # Choose template
    template_file = f"jenkins/templates/email_{args.status.lower()}.html"
    with open(template_file, 'r') as f:
        html = f.read()

    msg_html = MIMEText(html, 'html')
    msg.attach(msg_html)

    # Attach logo
    with open('jenkins/assets/company_logo.png', 'rb') as f:
        logo = MIMEImage(f.read())
        logo.add_header('Content-ID','<company_logo>')
        logo.add_header('Content-Disposition','inline', filename='company_logo.png')
        msg.attach(logo)

    # Attach log
    with open(args.log, 'rb') as f:
        log_part = MIMEApplication(f.read(), Name='docker_tagging.log')
        log_part['Content-Disposition'] = 'attachment; filename="docker_tagging.log"'
        msg.attach(log_part)

    s = smtplib.SMTP('localhost')
    s.send_message(msg)
    s.quit()
    print(f"Email sent to {args.recipients}")

if __name__ == "__main__":
    send_email()
