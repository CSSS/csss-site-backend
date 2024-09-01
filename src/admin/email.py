import os
import smtplib

# TODO: set this up
GMAIL_PASSWORD = os.environ.get("GMAIL_PASSWORD")
GMAIL_ADDRESS = "csss-site@gmail.com"

# TODO: look into sending emails from an sfu maillist (this might be painful)
def send_email(
    recipient_address: str,
    subject: str,
    contents: str,
):
    mail = smtplib.SMTP("smtp.gmail.com", 587)
    mail.ehlo()
    mail.starttls()
    mail.login(GMAIL_ADDRESS, GMAIL_PASSWORD)

    header = f"To: {recipient_address}\nFrom: {GMAIL_USERNAME}\nSubject: {subject}"
    content = header + content

    mail.sendmail(GMAIL_ADDRESS, recipient_address, content)
    mail.quit()

