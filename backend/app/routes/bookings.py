# app/routes/bookings.py — /api/bookings/*
# User booking flow: create, view, cancel

from flask import Blueprint, request, g

from app.middleware.auth_middleware import require_auth
from app.middleware.validation import validate_request, BookingSchema
from app.services.booking_service import (
    book_slot, cancel_booking, get_user_active_booking
)
from app.utils.db import execute_one, execute_query
from app.utils.response import success, created, error, not_found, conflict

bookings_bp = Blueprint("bookings", __name__)

# Human-readable error messages for booking procedure result codes
BOOKING_ERRORS = {
    1: "You already have an active booking. Please cancel it before booking a new slot.",
    2: "This slot is fully booked. Please choose another slot.",
    3: "This job posting is no longer accepting bookings.",
    4: "You have already booked this slot.",
}


@bookings_bp.route("", methods=["POST"])
@require_auth
def create_booking():
    """
    Books a slot for the authenticated user.
    Enforces: one active booking per user at a time.
    """
    data, errs = validate_request(BookingSchema, request.get_json() or {})
    if errs:
        return error("Validation failed.", 422, errs)

    # Get user's DB id from Cognito sub
    user = execute_one(
        "SELECT id FROM users WHERE cognito_sub = :sub",
        {"sub": g.current_user["sub"]}
    )
    if not user:
        return error("User profile not found. Please complete registration.", 404)

    result = book_slot(
        user_id = user["id"],
        job_id  = data["job_id"],
        slot_id = data["slot_id"],
    )

    if not result["success"]:
        code    = result["error_code"]
        message = BOOKING_ERRORS.get(code, "Booking failed. Please try again.")
        return conflict(message) if code in (1, 4) else error(message, 400)

    return created(
        result["booking"],
        "Slot booked successfully! Confirmation email sent."
    )


@bookings_bp.route("/my", methods=["GET"])
@require_auth
def my_bookings():
    """Returns the current user's full booking history."""
    user = execute_one(
        "SELECT id FROM users WHERE cognito_sub = :sub",
        {"sub": g.current_user["sub"]}
    )
    if not user:
        return not_found("User not found.")

    bookings = execute_query(
        """
        SELECT b.id, b.status, b.confirmation_code, b.booked_at,
               j.role_title, j.interview_date, j.venue_address,
               c.company_name,
               s.start_time, s.end_time
        FROM   bookings b
        JOIN   jobs      j ON j.id = b.job_id
        JOIN   companies c ON c.id = j.company_id
        JOIN   slots     s ON s.id = b.slot_id
        WHERE  b.user_id = :uid
        ORDER  BY b.booked_at DESC
        """,
        {"uid": user["id"]}
    )
    return success(bookings)


@bookings_bp.route("/active", methods=["GET"])
@require_auth
def active_booking():
    """Returns the user's current active booking (if any)."""
    user = execute_one(
        "SELECT id FROM users WHERE cognito_sub = :sub",
        {"sub": g.current_user["sub"]}
    )
    if not user:
        return not_found("User not found.")

    booking = get_user_active_booking(user["id"])
    return success(booking)  # Returns null if no active booking — that's fine


@bookings_bp.route("/<int:booking_id>", methods=["DELETE"])
@require_auth
def cancel_user_booking(booking_id: int):
    """Cancels a booking. Only the booking owner can cancel."""
    user = execute_one(
        "SELECT id FROM users WHERE cognito_sub = :sub",
        {"sub": g.current_user["sub"]}
    )
    if not user:
        return not_found("User not found.")

    result = cancel_booking(booking_id, user["id"])

    if not result["success"]:
        return error(result["message"], 400)

    return success(message=result["message"])


@bookings_bp.route("/<string:code>", methods=["GET"])
def get_by_code(code: str):
    """Public lookup — fetches booking details by confirmation code."""
    booking = execute_one(
        """
        SELECT b.status, b.confirmation_code, b.booked_at,
               j.role_title, j.interview_date, j.venue_address,
               c.company_name,
               s.start_time, s.end_time,
               u.full_name AS candidate_name
        FROM   bookings b
        JOIN   jobs      j ON j.id = b.job_id
        JOIN   companies c ON c.id = j.company_id
        JOIN   slots     s ON s.id = b.slot_id
        JOIN   users     u ON u.id = b.user_id
        WHERE  b.confirmation_code = :code
        """,
        {"code": code.upper()}
    )
    if not booking:
        return not_found("Booking not found.")
    return success(booking)