# coding=utf-8

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import SMTP_HOST, FROM_USER, EXMAIL_PASSWORD


def send_mail_task(msg):
    from handler.tasks import send_email
    mp = MIMEMultipart('alternative')
    mp['Subject'] = msg.subject
    mp['From'] = FROM_USER
    mp['To'] = ','.join(msg.recipients)
    mp.attach(MIMEText(msg.html, 'html'))

    send_email.delay(SMTP_HOST, FROM_USER, EXMAIL_PASSWORD, msg.recipients,
                     mp.as_string())
