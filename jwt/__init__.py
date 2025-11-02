import base64
import json

class PyJWTError(Exception):
    pass

class DecodeError(PyJWTError):
    pass

class ExpiredSignatureError(PyJWTError):
    pass


def encode(payload, key, algorithm="HS256"):
    data = json.dumps(payload).encode("utf-8")
    return base64.urlsafe_b64encode(data).decode("utf-8")


def decode(token, key, algorithms=None, options=None):
    try:
        data = base64.urlsafe_b64decode(token.encode("utf-8"))
        return json.loads(data)
    except Exception as exc:  # pragma: no cover - defensive
        raise DecodeError(str(exc)) from exc
