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
# @require_auth
def create_booking():
    print("USER:", g.get("current_user"))

    data, errs = validate_request(BookingSchema, request.get_json() or {})
    if errs:
        return error("Validation failed.", 422, errs)

    user = execute_one(
        "SELECT id FROM users WHERE cognito_sub = :sub",
        {"sub": g.current_user["sub"]}
    )
    if not user:
        return error("User profile not found.", 404)

    result = book_slot(
        user_id=user["id"],
        job_id=data["job_id"],
        slot_id=data["slot_id"],
    )

    if not result["success"]:
        code = result["error_code"]
        message = BOOKING_ERRORS.get(code, "Booking failed.")
        return conflict(message) if code in (1, 4) else error(message, 400)

    # ✅ FIX
    def serialize_booking(b):
        b = dict(b)
        if b.get("booked_at"):
            b["booked_at"] = str(b["booked_at"])
        if b.get("start_time"):
            b["start_time"] = str(b["start_time"])
        if b.get("end_time"):
            b["end_time"] = str(b["end_time"])
        return b

    booking = serialize_booking(result["booking"])

    return created(
        booking,
        "Slot booked successfully! Confirmation email sent."
    )

@bookings_bp.route("/my", methods=["GET"])
@require_auth
def my_bookings():
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
        FROM bookings b
        JOIN jobs j ON j.id = b.job_id
        JOIN companies c ON c.id = j.company_id
        JOIN slots s ON s.id = b.slot_id
        WHERE b.user_id = :uid
        ORDER BY b.booked_at DESC
        """,
        {"uid": user["id"]}
    )

    # ✅ FIX
    def serialize_row(r):
        r = dict(r)
        if r.get("booked_at"):
            r["booked_at"] = str(r["booked_at"])
        if r.get("start_time"):
            r["start_time"] = str(r["start_time"])
        if r.get("end_time"):
            r["end_time"] = str(r["end_time"])
        return r

    bookings = [serialize_row(b) for b in bookings]

    return success(bookings)

@bookings_bp.route("/active", methods=["GET"])
# @require_auth
def active_booking():
    print("USER:", g.get("current_user"))
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
        return not_found("Booking not found.")   # ✅ fixed indent

    # ✅ FIX HERE
    booking = dict(booking)

    if booking.get("booked_at"):
        booking["booked_at"] = str(booking["booked_at"])

    if booking.get("start_time"):
        booking["start_time"] = str(booking["start_time"])

    if booking.get("end_time"):
        booking["end_time"] = str(booking["end_time"])

    return success(booking)