from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadTimeSignature
from flask import current_app

def generate_confirmation_token(email):
    serializer = URLSafeTimedSerializer(current_app.secret_key)
    token = serializer.dumps(email, salt="email-confirm-salt")
    return token

def confirm_token(token, expiration=3600):
    serializer = URLSafeTimedSerializer(current_app.secret_key)
    try:
        email = serializer.loads(
            token,
            salt="email-confirm-salt",
            max_age=expiration
        )
        return email
    except SignatureExpired:
        return False
    except BadTimeSignature:
        return False
    except Exception as e:
        return False