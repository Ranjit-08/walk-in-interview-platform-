# app/services/cognito_service.py
# Wraps all AWS Cognito Identity Provider calls:
# sign-up, confirm, login, logout, password reset

import boto3
import hmac
import hashlib
import base64
import logging
from botocore.exceptions import ClientError
from flask import current_app

logger = logging.getLogger(__name__)


def _get_client():
    return boto3.client(
        "cognito-idp",
        region_name=current_app.config["COGNITO_REGION"]
    )


def _compute_secret_hash(username: str) -> str:
    """
    Computes the SECRET_HASH required by Cognito when a client secret is set.
    """
    client_id     = current_app.config["COGNITO_APP_CLIENT_ID"]
    client_secret = current_app.config.get("COGNITO_APP_CLIENT_SECRET", "")
    if not client_secret:
        return None

    message = username + client_id
    digest  = hmac.new(
        client_secret.encode("utf-8"),
        message.encode("utf-8"),
        digestmod=hashlib.sha256
    ).digest()
    return base64.b64encode(digest).decode()


def register_user(email: str, password: str, full_name: str,
                  phone: str = None, role: str = "user") -> dict:
    """
    Registers a new user in the Cognito User Pool.
    Returns { "user_sub": "...", "confirmed": bool }
    """
    client    = _get_client()
    client_id = current_app.config["COGNITO_APP_CLIENT_ID"]

    user_attributes = [
        {"Name": "email",        "Value": email},
        {"Name": "name",         "Value": full_name},
        {"Name": "custom:role",  "Value": role},
    ]
    if phone:
        user_attributes.append({"Name": "phone_number", "Value": phone})

    kwargs = {
        "ClientId":       client_id,
        "Username":       email,
        "Password":       password,
        "UserAttributes": user_attributes,
    }

    secret_hash = _compute_secret_hash(email)
    if secret_hash:
        kwargs["SecretHash"] = secret_hash

    response = client.sign_up(**kwargs)
    return {
        "user_sub":  response["UserSub"],
        "confirmed": response["UserConfirmed"],
    }


def confirm_signup(email: str, code: str) -> bool:
    """Confirms the email verification code sent by Cognito."""
    client    = _get_client()
    client_id = current_app.config["COGNITO_APP_CLIENT_ID"]

    kwargs = {
        "ClientId":         client_id,
        "Username":         email,
        "ConfirmationCode": code,
    }
    secret_hash = _compute_secret_hash(email)
    if secret_hash:
        kwargs["SecretHash"] = secret_hash

    client.confirm_sign_up(**kwargs)
    return True


def login_user(email: str, password: str) -> dict:
    """
    Authenticates a user with Cognito.
    Returns { "access_token", "id_token", "refresh_token", "expires_in" }
    """
    client    = _get_client()
    client_id = current_app.config["COGNITO_APP_CLIENT_ID"]

    auth_params = {
        "USERNAME": email,
        "PASSWORD": password,
    }
    secret_hash = _compute_secret_hash(email)
    if secret_hash:
        auth_params["SECRET_HASH"] = secret_hash

    response = client.initiate_auth(
        ClientId=client_id,
        AuthFlow="USER_PASSWORD_AUTH",
        AuthParameters=auth_params,
    )

    result = response["AuthenticationResult"]
    return {
        "access_token":  result["AccessToken"],
        "id_token":      result["IdToken"],
        "refresh_token": result["RefreshToken"],
        "expires_in":    result["ExpiresIn"],
        "token_type":    result["TokenType"],
    }


def logout_user(access_token: str) -> bool:
    """Globally signs out a user (invalidates all tokens)."""
    client = _get_client()
    client.global_sign_out(AccessToken=access_token)
    return True


def forgot_password(email: str) -> bool:
    """Triggers the Cognito forgot-password flow (sends reset code)."""
    client    = _get_client()
    client_id = current_app.config["COGNITO_APP_CLIENT_ID"]

    kwargs = {"ClientId": client_id, "Username": email}
    secret_hash = _compute_secret_hash(email)
    if secret_hash:
        kwargs["SecretHash"] = secret_hash

    client.forgot_password(**kwargs)
    return True


def confirm_forgot_password(email: str, code: str, new_password: str) -> bool:
    """Confirms the password reset with the verification code."""
    client    = _get_client()
    client_id = current_app.config["COGNITO_APP_CLIENT_ID"]

    kwargs = {
        "ClientId":         client_id,
        "Username":         email,
        "ConfirmationCode": code,
        "Password":         new_password,
    }
    secret_hash = _compute_secret_hash(email)
    if secret_hash:
        kwargs["SecretHash"] = secret_hash

    client.confirm_forgot_password(**kwargs)
    return True