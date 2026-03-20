# app/routes/auth.py — /api/auth/*
# Handles user and company registration, login, logout, password reset

from flask import Blueprint, request, g
from botocore.exceptions import ClientError

from app.middleware.auth_middleware import require_auth
from app.middleware.validation import (
    validate_request, UserRegisterSchema,
    CompanyRegisterSchema, LoginSchema
)
from app.services import cognito_service
from app.utils.db import execute_one, execute_write
from app.utils.response import success, created, error, unauthorized, conflict

auth_bp = Blueprint("auth", __name__)


# ── User Registration ──────────────────────────────────────────────────────────

@auth_bp.route("/register/user", methods=["POST"])
def register_user():
    """Register a new candidate user."""
    data, errs = validate_request(UserRegisterSchema, request.get_json() or {})
    if errs:
        return error("Validation failed.", 422, errs)

    # Check if email already exists in our DB
    existing = execute_one(
        "SELECT id FROM users WHERE email = :email",
        {"email": data["email"]}
    )
    if existing:
        return conflict("An account with this email already exists.")

    try:
        cognito_result = cognito_service.register_user(
            email     = data["email"],
            password  = data["password"],
            full_name = data["full_name"],
            phone     = data.get("phone"),
            role      = "user",
        )
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code == "UsernameExistsException":
            return conflict("An account with this email already exists.")
        return error(e.response["Error"]["Message"], 400)

    # Insert into local DB (Cognito sub as FK)
    execute_write(
        """
        INSERT INTO users (cognito_sub, email, full_name, phone)
        VALUES (:sub, :email, :name, :phone)
        """,
        {
            "sub":   cognito_result["user_sub"],
            "email": data["email"],
            "name":  data["full_name"],
            "phone": data.get("phone"),
        }
    )

    return created(
        {"email": data["email"], "confirmed": cognito_result["confirmed"]},
        "Registration successful. Please check your email to verify your account."
    )


# ── Company Registration ───────────────────────────────────────────────────────

@auth_bp.route("/register/company", methods=["POST"])
def register_company():
    """Register a new company recruiter account."""
    data, errs = validate_request(CompanyRegisterSchema, request.get_json() or {})
    if errs:
        return error("Validation failed.", 422, errs)

    existing = execute_one(
        "SELECT id FROM companies WHERE email = :email",
        {"email": data["email"]}
    )
    if existing:
        return conflict("A company account with this email already exists.")

    try:
        cognito_result = cognito_service.register_user(
            email        = data["email"],
            password     = data["password"],
            full_name    = data["company_name"],
            role         = "company",
        )
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code == "UsernameExistsException":
            return conflict("A company account with this email already exists.")
        return error(e.response["Error"]["Message"], 400)

    execute_write(
        """
        INSERT INTO companies (cognito_sub, company_name, email, industry, website)
        VALUES (:sub, :name, :email, :industry, :website)
        """,
        {
            "sub":      cognito_result["user_sub"],
            "name":     data["company_name"],
            "email":    data["email"],
            "industry": data.get("industry"),
            "website":  data.get("website"),
        }
    )

    return created(
        {"email": data["email"]},
        "Company registration successful. Please verify your email."
    )


# ── Email Verification ─────────────────────────────────────────────────────────

@auth_bp.route("/confirm", methods=["POST"])
def confirm_email():
    """Confirms Cognito email with the verification code."""
    body = request.get_json() or {}
    email = body.get("email", "").strip()
    code  = body.get("code",  "").strip()

    if not email or not code:
        return error("Email and confirmation code are required.", 422)

    try:
        cognito_service.confirm_signup(email, code)
        return success(message="Email verified. You can now log in.")
    except ClientError as e:
        return error(e.response["Error"]["Message"], 400)


# ── Login ──────────────────────────────────────────────────────────────────────

@auth_bp.route("/login", methods=["POST"])
def login():
    """Authenticates user or company and returns Cognito tokens."""
    data, errs = validate_request(LoginSchema, request.get_json() or {})
    if errs:
        return error("Validation failed.", 422, errs)

    try:
        tokens = cognito_service.login_user(data["email"], data["password"])
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code in ("NotAuthorizedException", "UserNotFoundException"):
            return unauthorized("Invalid email or password.")
        if code == "UserNotConfirmedException":
            return error("Please verify your email before logging in.", 403)
        return error(e.response["Error"]["Message"], 400)

    # Fetch user profile from our DB (could be user or company)
    profile = execute_one(
        "SELECT id, full_name, email, role FROM users WHERE email = :email",
        {"email": data["email"]}
    )
    if not profile:
        # Try companies table
        profile = execute_one(
            "SELECT id, company_name AS full_name, email, 'company' AS role "
            "FROM companies WHERE email = :email",
            {"email": data["email"]}
        )

    return success({
        **tokens,
        "profile": profile,
    }, "Login successful.")


# ── Logout ─────────────────────────────────────────────────────────────────────

@auth_bp.route("/logout", methods=["POST"])
@require_auth
def logout():
    """Globally invalidates the user's Cognito session."""
    auth_header  = request.headers.get("Authorization", "")
    access_token = auth_header.split(" ", 1)[1] if " " in auth_header else ""
    try:
        cognito_service.logout_user(access_token)
        return success(message="Logged out successfully.")
    except ClientError as e:
        return error(e.response["Error"]["Message"], 400)


# ── Forgot Password ────────────────────────────────────────────────────────────

@auth_bp.route("/forgot-password", methods=["POST"])
def forgot_password():
    body  = request.get_json() or {}
    email = body.get("email", "").strip()
    if not email:
        return error("Email is required.", 422)
    try:
        cognito_service.forgot_password(email)
        return success(message="Password reset code sent to your email.")
    except ClientError as e:
        # Don't reveal whether the account exists
        return success(message="If this email is registered, a reset code has been sent.")


@auth_bp.route("/reset-password", methods=["POST"])
def reset_password():
    body     = request.get_json() or {}
    email    = body.get("email",        "").strip()
    code     = body.get("code",         "").strip()
    password = body.get("new_password", "").strip()

    if not all([email, code, password]) or len(password) < 8:
        return error("Email, code, and a new password (min 8 chars) are required.", 422)

    try:
        cognito_service.confirm_forgot_password(email, code, password)
        return success(message="Password reset successful. You can now log in.")
    except ClientError as e:
        return error(e.response["Error"]["Message"], 400)


# ── Profile ────────────────────────────────────────────────────────────────────

@auth_bp.route("/me", methods=["GET"])
@require_auth
def get_profile():
    """Returns the current user's profile from DB."""
    sub = g.current_user["sub"]

    profile = execute_one(
        "SELECT id, email, full_name, phone, role, created_at "
        "FROM users WHERE cognito_sub = :sub",
        {"sub": sub}
    )
    if not profile:
        profile = execute_one(
            "SELECT id, email, company_name, industry, website, created_at "
            "FROM companies WHERE cognito_sub = :sub",
            {"sub": sub}
        )
    if not profile:
        return error("Profile not found.", 404)

    return success(profile)