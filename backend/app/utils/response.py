# app/utils/response.py — Standardised JSON response helpers
# Every API endpoint uses these to keep response shape consistent

from flask import jsonify


def success(data=None, message="Success", status_code=200):
    """
    Standard success response.
    Shape: { "success": true, "message": "...", "data": {...} }
    """
    response = {
        "success": True,
        "message": message,
    }
    if data is not None:
        response["data"] = data
    return jsonify(response), status_code


def created(data=None, message="Created successfully"):
    return success(data, message, 201)


def error(message="An error occurred", status_code=400, errors=None):
    """
    Standard error response.
    Shape: { "success": false, "message": "...", "errors": [...] }
    """
    response = {
        "success": False,
        "message": message,
    }
    if errors:
        response["errors"] = errors
    return jsonify(response), status_code


def unauthorized(message="Unauthorised. Please log in."):
    return error(message, 401)


def forbidden(message="Forbidden. You do not have permission."):
    return error(message, 403)


def not_found(message="Resource not found."):
    return error(message, 404)


def conflict(message="Conflict. Resource already exists."):
    return error(message, 409)


def server_error(message="Internal server error."):
    return error(message, 500)