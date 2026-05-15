import uuid
from datetime import datetime, timedelta

def generate_tokens(emails, test_id):
    tokens = {}
    for email in emails:
        token = str(uuid.uuid4())
        tokens[email] = token
    return tokens

def is_test_active(start, end):
    now = datetime.now()
    return start <= now <= end