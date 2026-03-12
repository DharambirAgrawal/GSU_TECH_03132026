import requests as req
from settings import POWERAUTOMATE_EMAIL_API_URL


def send_email(recipient, subject, message):
    body = {
        "subject": subject,
        "recipient": recipient,
        "message": message.replace("\n", "<br>"),
    }
    try:
        response = req.post(POWERAUTOMATE_EMAIL_API_URL, json=body)
        if response.status_code != 200:
            raise Exception(
                "Response is not 200, email must have failed to send, check power automate flow logs"
            )
    except Exception as e:
        # Do exponential back-off retry later
        raise
