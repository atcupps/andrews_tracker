# Handles scraping errors or failures

import os
import smtplib
from email.message import EmailMessage

class Handler:
    def __init__(self):
        self.from_email = os.environ['HANDLER_EMAIL']
        self.from_password = os.environ['HANDLER_PASSWORD']
        self.to_email = os.environ['DEST_EMAIL']
        self.failures = [] # List of failed courses
    
    # Add a course to list of failed courses
    def add_failed_course(self, course):
        self.failures += [course]
    
    # Send email if necessary
    def send_email(self):
        if len(self.failures) > 0:
            msg = EmailMessage()
            msg['Subject'] = '🚨 URGENT 🚨: Seat tracking failure alert'
            msg['From'] = self.from_email
            msg['To'] = self.to_email
            msg.set_content(f'Seat tracking failed for {len(self.failures)} courses: {self.failures}')

            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
                smtp.login(self.from_email, self.from_password)
                smtp.send_message(msg)