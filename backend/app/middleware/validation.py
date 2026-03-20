# app/middleware/validation.py — Input validation helpers
# Uses marshmallow schemas to validate and sanitise request data

from marshmallow import Schema, fields, validate, ValidationError, pre_load
import re


# ── Schemas ────────────────────────────────────────────────────────────────────

class UserRegisterSchema(Schema):
    email       = fields.Email(required=True)
    password    = fields.Str(required=True, validate=validate.Length(min=8, max=128))
    full_name   = fields.Str(required=True, validate=validate.Length(min=2, max=150))
    phone       = fields.Str(load_default=None, validate=validate.Regexp(
        r"^\+?[1-9]\d{9,14}$", error="Invalid phone number format."
    ))

    @pre_load
    def strip_strings(self, data, **kwargs):
        return {k: v.strip() if isinstance(v, str) else v for k, v in data.items()}


class CompanyRegisterSchema(Schema):
    email        = fields.Email(required=True)
    password     = fields.Str(required=True, validate=validate.Length(min=8, max=128))
    company_name = fields.Str(required=True, validate=validate.Length(min=2, max=200))
    industry     = fields.Str(load_default=None, validate=validate.Length(max=100))
    website      = fields.Url(load_default=None, require_tld=True)

    @pre_load
    def strip_strings(self, data, **kwargs):
        return {k: v.strip() if isinstance(v, str) else v for k, v in data.items()}


class LoginSchema(Schema):
    email    = fields.Email(required=True)
    password = fields.Str(required=True)


class JobPostSchema(Schema):
    role_title          = fields.Str(required=True, validate=validate.Length(min=2, max=200))
    job_description     = fields.Str(required=True, validate=validate.Length(min=10))
    requirements        = fields.Str(load_default=None)
    package_lpa         = fields.Float(required=True, validate=validate.Range(min=0.5, max=500))
    experience_min_yrs  = fields.Float(load_default=0, validate=validate.Range(min=0, max=50))
    experience_max_yrs  = fields.Float(load_default=None, validate=validate.Range(min=0, max=50))
    interview_date      = fields.Date(required=True)
    venue_address       = fields.Str(load_default=None)
    candidates_required = fields.Int(required=True, validate=validate.Range(min=1, max=10000))
    slots               = fields.List(fields.Dict(), required=True, validate=validate.Length(min=1))


class BookingSchema(Schema):
    job_id  = fields.Int(required=True, validate=validate.Range(min=1))
    slot_id = fields.Int(required=True, validate=validate.Range(min=1))


class InterviewMessageSchema(Schema):
    session_id  = fields.Int(load_default=None)
    job_id      = fields.Int(load_default=None)
    message     = fields.Str(required=True, validate=validate.Length(min=1, max=2000))
    history     = fields.List(fields.Dict(), load_default=[])


# ── Validator helper ────────────────────────────────────────────────────────────

def validate_request(schema_class, data: dict):
    """
    Validates a dict against a marshmallow schema.
    Returns (cleaned_data, None) on success.
    Returns (None, error_dict) on failure.
    """
    schema = schema_class()
    try:
        cleaned = schema.load(data)
        return cleaned, None
    except ValidationError as err:
        return None, err.messages