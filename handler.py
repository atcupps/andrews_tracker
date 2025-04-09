# Handles scraping errors or failures

import os
import smtplib
from email.message import EmailMessage

class Handler:
    def __init__(self):
        self.from_email = os.environ['HANDLER_EMAIL']
        self.from_password = os.environ['HANDLER_PASSWORD']
        self.to_email = os.environ['DEST_EMAIL']
        self.errors = [] # List of errors

    '''
    Add an error: request failed
    '''
    def error_request_failed(self, url):
        self.errors += [('REQUEST FAILED', url)]

    '''
    Add an error: Supabase error
    '''
    def error_supabase(self, error):
        self.errors += [('SUPABASE ERROR', error)]
    
    '''
    Assemble content string for email
    '''
    def assemble_string(self):
        errors_as_strings = map(
            lambda err: f'<strong>{err[0]}</strong><br>{err[1]}', self.errors
        )
        return '<br><br>'.join(errors_as_strings)
    
    # Send email if necessary
    def send_email(self):
        if len(self.errors) > 0:
            msg = EmailMessage()
            msg['Subject'] = '🚨 URGENT 🚨: Seat tracking failure alert'
            msg['From'] = self.from_email
            msg['To'] = self.to_email
            msg.set_content(self.assemble_string())

            # with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            #     smtp.login(self.from_email, self.from_password)
            #     smtp.send_message(msg)
            print(msg.get_content())