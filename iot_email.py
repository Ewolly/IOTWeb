import sendgrid
import os
from sendgrid.helpers.mail import *


def send_mail(email, subject, contents, apikey):
    sg = sendgrid.SendGridAPIClient(apikey=apikey)
    from_email = Email("support@iot.duality.co.nz")
    to_email = Email(email)
    content = Content("text/html", contents)
    mail = Mail(from_email, subject, to_email, content)
    response = sg.client.mail.send.post(request_body=mail.get())
    return(response.status_code)