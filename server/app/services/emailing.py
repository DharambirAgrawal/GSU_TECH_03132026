import requests as req

from settings import POWERAUTOMATE_EMAIL_API_URL

# Hard cap on how long we wait for the Power Automate webhook.
# Prevents magic-link requests from hanging if the flow is slow or misconfigured.
_REQUEST_TIMEOUT_SECONDS = 10


def send_email(recipient: str, subject: str, message: str) -> None:
    """
    Send an email via the Power Automate HTTP trigger webhook.

    The recipient address is rewritten to @gmail.com before dispatch.
    This is intentional for dev/testing — real company emails route
    to personal Gmail inboxes so team members can test without a
    corporate email server.

    Example:
        admin@amazon.com  →  admin@gmail.com  (actual delivery target)

    Args:
        recipient: Original email address (domain gets replaced with @gmail.com).
        subject:   Email subject line.
        message:   Plain-text body. Newlines are converted to <br> for HTML.

    Raises:
        ValueError: If POWERAUTOMATE_EMAIL_API_URL is not configured.
        Exception:  If the Power Automate call returns a non-200 status.
    """
    if not POWERAUTOMATE_EMAIL_API_URL:
        raise ValueError(
            "POWERAUTOMATE_EMAIL_API_URL is not set. "
            "Add it to your .env file to enable email delivery."
        )

    # Rewrite domain to gmail for dev/test delivery
    gmail_recipient = recipient.split("@")[0] + "@gmail.com"

    body = {
        "subject": subject,
        "recipient": gmail_recipient,
        "message": message.replace("\n", "<br>"),
    }

    response = req.post(
        POWERAUTOMATE_EMAIL_API_URL,
        json=body,
        timeout=_REQUEST_TIMEOUT_SECONDS,
    )

    if response.status_code != 200:
        raise Exception(
            f"Power Automate returned {response.status_code}. "
            "Email may not have been sent — check Power Automate flow logs."
        )
