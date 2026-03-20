# app/middleware/auth_middleware.py
# Verifies AWS Cognito JWT tokens on protected routes.
# Decodes the token, fetches Cognito JWKS, and validates the signature.

import json
import time
import urllib.request
from functools import wraps

import jwt
from jwt.algorithms import RSAAlgorithm
from flask import request, current_app, g

from app.utils.response import unauthorized

# Cache JWKS in memory so we don't fetch it on every request
_jwks_cache = {}


def _get_jwks(pool_id: str, region: str) -> dict:
    """
    Fetches and caches the Cognito JWKS (public keys).
    """
    cache_key = f"{region}_{pool_id}"
    if cache_key not in _jwks_cache:
        url = (
            f"https://cognito-idp.{region}.amazonaws.com"
            f"/{pool_id}/.well-known/jwks.json"
        )
        with urllib.request.urlopen(url) as resp:
            _jwks_cache[cache_key] = json.loads(resp.read())
    return _jwks_cache[cache_key]


def _decode_token(token: str) -> dict:
    """
    Validates and decodes a Cognito JWT access token.
    Raises jwt.PyJWTError on failure.
    """
    region    = current_app.config["COGNITO_REGION"]
    pool_id   = current_app.config["COGNITO_USER_POOL_ID"]
    client_id = current_app.config["COGNITO_APP_CLIENT_ID"]

    # Decode header to get the key id (kid)
    header = jwt.get_unverified_header(token)
    kid    = header.get("kid")

    # Find the matching public key in JWKS
    jwks = _get_jwks(pool_id, region)
    public_key = None
    for key_data in jwks.get("keys", []):
        if key_data["kid"] == kid:
            public_key = RSAAlgorithm.from_jwk(json.dumps(key_data))
            break

    if not public_key:
        raise jwt.InvalidKeyError("Public key not found in JWKS.")

    # Decode and verify the token
    payload = jwt.decode(
        token,
        public_key,
        algorithms=["RS256"],
        audience=client_id,
        options={"verify_exp": True}
    )

    return payload


def require_auth(f):
    """
    Decorator for routes that require a valid Cognito JWT.
    Sets g.current_user = { "sub": ..., "email": ..., "role": ... }
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return unauthorized("Missing or malformed Authorization header.")

        token = auth_header.split(" ", 1)[1]

        try:
            payload = _decode_token(token)
        except jwt.ExpiredSignatureError:
            return unauthorized("Token has expired. Please log in again.")
        except jwt.PyJWTError as e:
            return unauthorized(f"Invalid token: {str(e)}")

        # Store decoded user info on Flask's request context
        g.current_user = {
            "sub":   payload.get("sub"),
            "email": payload.get("email"),
            "role":  payload.get("custom:role", "user"),
        }
        return f(*args, **kwargs)

    return decorated


def require_company(f):
    """
    Decorator for company-only routes.
    Must be used AFTER @require_auth.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if not hasattr(g, "current_user"):
            return unauthorized()
        if g.current_user.get("role") != "company":
            return unauthorized("This endpoint is restricted to company accounts.")
        return f(*args, **kwargs)
    return decorated


def require_admin(f):
    """Decorator for admin-only routes."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not hasattr(g, "current_user"):
            return unauthorized()
        if g.current_user.get("role") != "admin":
            return unauthorized("Admin access required.")
        return f(*args, **kwargs)
    return decorated