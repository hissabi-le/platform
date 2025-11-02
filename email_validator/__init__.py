__version__ = "2.0.0"

class EmailNotValidError(ValueError):
    pass

def validate_email(email, **kwargs):
    if not isinstance(email, str) or "@" not in email:
        raise EmailNotValidError("Invalid email address")
    return {"email": email.lower()}
