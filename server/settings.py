import os

import dotenv

dotenv.load_dotenv()

POWERAUTOMATE_EMAIL_API_URL = os.getenv("POWERAUTOMATE_EMAIL_API_URL")
