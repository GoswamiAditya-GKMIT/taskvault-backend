import secrets
import string

def generate_otp(length=6):
    # Generates a string of digits (e.g., '012345')
    return ''.join(secrets.choice(string.digits) for _ in range(length))

