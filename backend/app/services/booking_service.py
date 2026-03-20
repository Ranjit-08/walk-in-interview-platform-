# app/services/booking_service.py
# All booking business logic lives here.
# Handles: constraint checks, slot booking, cancellation, status updates.

import shortuuid
import logging
from datetime import date
from flask import current_app

from app.utils.db import execute_one, execute_query, execute_write, call_procedure
from app.services.ses_service import send_booking_confirmation, send_booking_cancellation

logger = logging.getLogger(__name__)


def generate_confirmation_code() -> str:
    """Generates a unique booking confirmation code e.g. WI-ABC12345."""
    prefix = current_app.config.get("BOOKING_CODE_PREFIX", "WI")
    uid    = shortuuid.ShortUUID().random(length=8).upper()
    return f"{prefix}-{uid}"


def get_user_active_booking(user_id: int) -> dict | None:
    """
    Returns the user's current active (confirmed) booking, or None.
    This is used to enforce the one-active-booking constraint.
    """
    return execute_one(
        """
        SELECT b.*, j.role_title, j.interview_date,
               c.company_name,
               s.start_time, s.end_time
        FROM   bookings b
        JOIN   jobs  j ON j.id = b.job_id
        JOIN   companies c ON c.id = j.company_id
        JOIN   slots s ON s.id = b.slot_id
        WHERE  b.user_id = :user_id
          AND  b.status  = 'confirmed'
        LIMIT  1
        """,
        {"user_id": user_id}
    )


def book_slot(user_id: int, job_id: int, slot_id: int) -> dict:
    """
    Books a slot for a user using the atomic stored procedure.

    Returns:
        { "success": bool, "booking": dict | None, "error_code": int | None }

    Error codes:
        1 = User already has an active booking
        2 = Slot is full
        3 = Job is not active
        4 = Duplicate booking
    """
    confirmation_code = generate_confirmation_code()

    # Call the stored procedure (handles atomicity + locking)
    result_code = call_procedure(
        "sp_book_slot",
        [user_id, job_id, slot_id, confirmation_code, 0]
    )
    result_code = int(result_code) if result_code is not None else 0

    if result_code != 0:
        return {"success": False, "booking": None, "error_code": result_code}

    # Fetch the newly created booking with full details
    booking = execute_one(
        """
        SELECT b.*, j.role_title, j.interview_date, j.venue_address,
               c.company_name, c.email AS company_email,
               u.email AS user_email, u.full_name AS user_name,
               s.start_time, s.end_time
        FROM   bookings b
        JOIN   jobs      j ON j.id = b.job_id
        JOIN   companies c ON c.id = j.company_id
        JOIN   users     u ON u.id = b.user_id
        JOIN   slots     s ON s.id = b.slot_id
        WHERE  b.confirmation_code = :code
        """,
        {"code": confirmation_code}
    )

    # Send confirmation email (non-blocking — failure doesn't cancel booking)
    if booking:
        try:
            sent = send_booking_confirmation(
                to_email          = booking["user_email"],
                user_name         = booking["user_name"],
                company_name      = booking["company_name"],
                role_title        = booking["role_title"],
                interview_date    = str(booking["interview_date"]),
                slot_start        = str(booking["start_time"]),
                slot_end          = str(booking["end_time"]),
                venue_address     = booking.get("venue_address"),
                confirmation_code = confirmation_code,
            )
            # Mark email as sent in DB
            execute_write(
                "UPDATE bookings SET email_sent = :sent WHERE confirmation_code = :code",
                {"sent": sent, "code": confirmation_code}
            )
        except Exception as e:
            logger.warning("Email notification failed: %s", str(e))

    return {"success": True, "booking": booking, "error_code": None}


def cancel_booking(booking_id: int, user_id: int) -> dict:
    """
    Cancels a booking. Validates ownership. Releases the slot capacity.
    Returns { "success": bool, "message": str }
    """
    # Fetch booking with ownership check
    booking = execute_one(
        """
        SELECT b.*, j.role_title, j.interview_date, c.company_name,
               u.email AS user_email, u.full_name AS user_name
        FROM   bookings b
        JOIN   jobs      j ON j.id = b.job_id
        JOIN   companies c ON c.id = j.company_id
        JOIN   users     u ON u.id = b.user_id
        WHERE  b.id = :bid AND b.user_id = :uid
        """,
        {"bid": booking_id, "uid": user_id}
    )

    if not booking:
        return {"success": False, "message": "Booking not found or access denied."}

    if booking["status"] != "confirmed":
        return {"success": False, "message": f"Cannot cancel a booking with status '{booking['status']}'."}

    # Check if interview date has already passed
    if booking["interview_date"] < date.today():
        return {"success": False, "message": "Cannot cancel a past interview booking."}

    # Update booking status
    execute_write(
        "UPDATE bookings SET status = 'cancelled' WHERE id = :bid",
        {"bid": booking_id}
    )

    # Release the slot capacity
    execute_write(
        """
        UPDATE slots
        SET    booked_count = GREATEST(booked_count - 1, 0),
               status       = 'available'
        WHERE  id = :sid
        """,
        {"sid": booking["slot_id"]}
    )

    # Decrement job booked_slots count
    execute_write(
        """
        UPDATE jobs
        SET    booked_slots = GREATEST(booked_slots - 1, 0)
        WHERE  id = :jid
        """,
        {"jid": booking["job_id"]}
    )

    # Send cancellation email
    try:
        send_booking_cancellation(
            to_email       = booking["user_email"],
            user_name      = booking["user_name"],
            company_name   = booking["company_name"],
            role_title     = booking["role_title"],
            interview_date = str(booking["interview_date"]),
        )
    except Exception as e:
        logger.warning("Cancellation email failed: %s", str(e))

    return {"success": True, "message": "Booking cancelled successfully."}