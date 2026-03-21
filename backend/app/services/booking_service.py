import shortuuid
import logging
from datetime import date
from flask import current_app
from app.utils.db import execute_one, execute_query, execute_write
from app.services.ses_service import send_booking_confirmation, send_booking_cancellation

logger = logging.getLogger(__name__)

def generate_confirmation_code():
    prefix = current_app.config.get("BOOKING_CODE_PREFIX", "WI")
    uid = shortuuid.ShortUUID().random(length=8).upper()
    return f"{prefix}-{uid}"

def get_user_active_booking(user_id):
    return execute_one(
        """
        SELECT b.*, j.role_title, j.interview_date,
               c.company_name, s.start_time, s.end_time
        FROM   bookings b
        JOIN   jobs j ON j.id = b.job_id
        JOIN   companies c ON c.id = j.company_id
        JOIN   slots s ON s.id = b.slot_id
        WHERE  b.user_id = :user_id AND b.status = 'confirmed'
        LIMIT  1
        """,
        {"user_id": user_id}
    )

def book_slot(user_id, job_id, slot_id):
    active = execute_one(
        "SELECT id FROM bookings WHERE user_id = :uid AND status = 'confirmed'",
        {"uid": user_id}
    )
    if active:
        return {"success": False, "booking": None, "error_code": 1}

    job = execute_one(
        "SELECT id FROM jobs WHERE id = :jid AND status = 'active'",
        {"jid": job_id}
    )
    if not job:
        return {"success": False, "booking": None, "error_code": 3}

    slot = execute_one(
        "SELECT id, capacity, booked_count FROM slots WHERE id = :sid AND job_id = :jid AND status = 'available'",
        {"sid": slot_id, "jid": job_id}
    )
    if not slot or slot["booked_count"] >= slot["capacity"]:
        return {"success": False, "booking": None, "error_code": 2}

    confirmation_code = generate_confirmation_code()
    booking_id = execute_write(
        """
        INSERT INTO bookings (user_id, job_id, slot_id, confirmation_code, status)
        VALUES (:user_id, :job_id, :slot_id, :code, 'confirmed')
        """,
        {"user_id": user_id, "job_id": job_id, "slot_id": slot_id, "code": confirmation_code}
    )

    new_count = slot["booked_count"] + 1
    new_status = 'full' if new_count >= slot["capacity"] else 'available'
    execute_write(
        "UPDATE slots SET booked_count = :count, status = :status WHERE id = :sid",
        {"count": new_count, "status": new_status, "sid": slot_id}
    )
    execute_write(
        "UPDATE jobs SET booked_slots = booked_slots + 1 WHERE id = :jid",
        {"jid": job_id}
    )

    booking = execute_one(
        """
        SELECT b.id, b.status, b.confirmation_code, b.booked_at,
               j.role_title, j.interview_date, j.venue_address,
               c.company_name, c.email AS company_email,
               u.email AS user_email, u.full_name AS user_name,
               s.start_time, s.end_time
        FROM   bookings b
        JOIN   jobs j ON j.id = b.job_id
        JOIN   companies c ON c.id = j.company_id
        JOIN   users u ON u.id = b.user_id
        JOIN   slots s ON s.id = b.slot_id
        WHERE  b.id = :bid
        """,
        {"bid": booking_id}
    )

    if booking:
        try:
            send_booking_confirmation(
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
        except Exception as e:
            logger.warning(f"Email failed: {e}")

    return {"success": True, "booking": booking, "error_code": None}

def cancel_booking(booking_id, user_id):
    booking = execute_one(
        """
        SELECT b.*, j.role_title, j.interview_date, c.company_name,
               u.email AS user_email, u.full_name AS user_name
        FROM   bookings b
        JOIN   jobs j ON j.id = b.job_id
        JOIN   companies c ON c.id = j.company_id
        JOIN   users u ON u.id = b.user_id
        WHERE  b.id = :bid AND b.user_id = :uid
        """,
        {"bid": booking_id, "uid": user_id}
    )
    if not booking:
        return {"success": False, "message": "Booking not found."}
    if booking["status"] != "confirmed":
        return {"success": False, "message": f"Cannot cancel '{booking['status']}' booking."}

    execute_write(
        "UPDATE bookings SET status = 'cancelled' WHERE id = :bid",
        {"bid": booking_id}
    )
    execute_write(
        "UPDATE slots SET booked_count = GREATEST(booked_count-1,0), status='available' WHERE id = :sid",
        {"sid": booking["slot_id"]}
    )
    execute_write(
        "UPDATE jobs SET booked_slots = GREATEST(booked_slots-1,0) WHERE id = :jid",
        {"jid": booking["job_id"]}
    )
    try:
        send_booking_cancellation(
            to_email       = booking["user_email"],
            user_name      = booking["user_name"],
            company_name   = booking["company_name"],
            role_title     = booking["role_title"],
            interview_date = str(booking["interview_date"]),
        )
    except Exception as e:
        logger.warning(f"Cancel email failed: {e}")

    return {"success": True, "message": "Booking cancelled successfully."}
