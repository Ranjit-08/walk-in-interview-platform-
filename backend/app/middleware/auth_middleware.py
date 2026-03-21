import json
import urllib.request
from functools import wraps
import jwt
from jwt.algorithms import RSAAlgorithm
from flask import request, current_app, g
from app.utils.response import unauthorized

_jwks_cache = {}

def _get_jwks(pool_id, region):
    cache_key = f"{region}_{pool_id}"
    if cache_key not in _jwks_cache:
        url = f"https://cognito-idp.{region}.amazonaws.com/{pool_id}/.well-known/jwks.json"
        with urllib.request.urlopen(url, timeout=10) as resp:
            _jwks_cache[cache_key] = json.loads(resp.read())
    return _jwks_cache[cache_key]

def _decode_token(token):
    region  = current_app.config["COGNITO_REGION"]
    pool_id = current_app.config["COGNITO_USER_POOL_ID"]
    header  = jwt.get_unverified_header(token)
    kid     = header.get("kid")
    jwks    = _get_jwks(pool_id, region)
    public_key = None
    for key_data in jwks.get("keys", []):
        if key_data["kid"] == kid:
            public_key = RSAAlgorithm.from_jwk(json.dumps(key_data))
            break
    if not public_key:
        raise jwt.InvalidKeyError("Public key not found")
    payload = jwt.decode(
        token,
        public_key,
        algorithms=["RS256"],
        options={"verify_exp": True, "verify_aud": False}
    )
    return payload

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return unauthorized("Missing Authorization header.")
        token = auth_header.split(" ", 1)[1]
        try:
            payload = _decode_token(token)
        except jwt.ExpiredSignatureError:
            return unauthorized("Token expired.")
        except Exception as e:
            current_app.logger.error(f"Token error: {str(e)}")
            return unauthorized(f"Invalid token: {str(e)}")
        g.current_user = {
            "sub":   payload.get("sub"),
            "email": payload.get("email"),
            "role":  payload.get("custom:role", "user"),
        }
        return f(*args, **kwargs)
    return decorated

def require_company(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not hasattr(g, "current_user"):
            return unauthorized()
        if g.current_user.get("role") != "company":
            return unauthorized("Company access only.")
        return f(*args, **kwargs)
    return decorated

def require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not hasattr(g, "current_user"):
            return unauthorized()
        if g.current_user.get("role") != "admin":
            return unauthorized("Admin access only.")
        return f(*args, **kwargs)
    return decorated
