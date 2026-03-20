# app/services/ses_service.py
# Sends transactional emails via AWS SES.
# All email templates are defined here as HTML strings.

import boto3
import logging
from flask import current_app

logger = logging.getLogger(__name__)


def _get_client():
    return boto3.client(
        "ses",
        region_name=current_app.config["SES_REGION"]
    )


def send_booking_confirmation(
    to_email:          str,
    user_name:         str,
    company_name:      str,
    role_title:        str,
    interview_date:    str,
    slot_start:        str,
    slot_end:          str,
    venue_address:     str,
    confirmation_code: str,
) -> bool:
    """
    Sends a booking confirmation email to the candidate.
    """
    subject = f"Interview Confirmed — {role_title} at {company_name}"

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family: Arial, sans-serif; color: #333; max-width: 600px; margin: 0 auto;">

      <div style="background: #1D9E75; padding: 24px; border-radius: 8px 8px 0 0;">
        <h1 style="color: #fff; margin: 0; font-size: 22px;">Interview Booking Confirmed</h1>
      </div>

      <div style="background: #f9f9f9; padding: 24px; border: 1px solid #e0e0e0;">
        <p style="font-size: 16px;">Hi <strong>{user_name}</strong>,</p>
        <p>Your walk-in interview has been successfully booked. Here are the details:</p>

        <table style="width:100%; border-collapse: collapse; margin: 16px 0;">
          <tr style="background:#fff; border: 1px solid #ddd;">
            <td style="padding:10px; font-weight:bold; width:40%;">Company</td>
            <td style="padding:10px;">{company_name}</td>
          </tr>
          <tr style="background:#f5f5f5; border: 1px solid #ddd;">
            <td style="padding:10px; font-weight:bold;">Role</td>
            <td style="padding:10px;">{role_title}</td>
          </tr>
          <tr style="background:#fff; border: 1px solid #ddd;">
            <td style="padding:10px; font-weight:bold;">Interview Date</td>
            <td style="padding:10px;">{interview_date}</td>
          </tr>
          <tr style="background:#f5f5f5; border: 1px solid #ddd;">
            <td style="padding:10px; font-weight:bold;">Time Slot</td>
            <td style="padding:10px;">{slot_start} – {slot_end}</td>
          </tr>
          <tr style="background:#fff; border: 1px solid #ddd;">
            <td style="padding:10px; font-weight:bold;">Venue</td>
            <td style="padding:10px;">{venue_address or "To be announced"}</td>
          </tr>
        </table>

        <div style="background:#e8f5e9; border-left: 4px solid #1D9E75;
                    padding: 12px 16px; margin: 16px 0; border-radius: 4px;">
          <strong>Confirmation Code: {confirmation_code}</strong>
          <br><small>Please show this code at the interview venue.</small>
        </div>

        <p style="color: #888; font-size: 13px;">
          You can cancel this booking from your dashboard at any time before the interview date.
        </p>
      </div>

      <div style="background:#eee; padding:12px; text-align:center;
                  font-size:12px; color:#999; border-radius: 0 0 8px 8px;">
        Walk-in Interview Platform &nbsp;|&nbsp; Powered by AWS
      </div>
    </body>
    </html>
    """

    text_body = (
        f"Interview Booking Confirmed\n\n"
        f"Company: {company_name}\n"
        f"Role: {role_title}\n"
        f"Date: {interview_date}\n"
        f"Time: {slot_start} - {slot_end}\n"
        f"Venue: {venue_address or 'TBA'}\n"
        f"Confirmation Code: {confirmation_code}\n"
    )

    try:
        _get_client().send_email(
            Source=current_app.config["SES_SENDER_EMAIL"],
            Destination={"ToAddresses": [to_email]},
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {
                    "Text": {"Data": text_body,  "Charset": "UTF-8"},
                    "Html": {"Data": html_body,  "Charset": "UTF-8"},
                },
            },
        )
        logger.info("Booking confirmation email sent to %s", to_email)
        return True
    except Exception as e:
        # Email failure should NOT block the booking — just log it
        logger.error("SES send_email failed: %s", str(e))
        return False


def send_booking_cancellation(
    to_email:       str,
    user_name:      str,
    company_name:   str,
    role_title:     str,
    interview_date: str,
) -> bool:
    """Notifies the candidate that their booking has been cancelled."""
    subject   = f"Booking Cancelled — {role_title} at {company_name}"
    text_body = (
        f"Hi {user_name},\n\n"
        f"Your booking for {role_title} at {company_name} "
        f"on {interview_date} has been cancelled.\n\n"
        f"You are now free to book another interview slot.\n"
    )
    html_body = f"""
    <html><body style="font-family:Arial,sans-serif;color:#333;max-width:600px;margin:0 auto;">
      <div style="background:#E24B4A;padding:24px;border-radius:8px 8px 0 0;">
        <h1 style="color:#fff;margin:0;font-size:20px;">Booking Cancelled</h1>
      </div>
      <div style="padding:24px;border:1px solid #eee;">
        <p>Hi <strong>{user_name}</strong>,</p>
        <p>Your booking for <strong>{role_title}</strong> at
           <strong>{company_name}</strong> on <strong>{interview_date}</strong>
           has been cancelled.</p>
        <p>You are now free to book a new interview slot from the platform.</p>
      </div>
    </body></html>
    """
    try:
        _get_client().send_email(
            Source=current_app.config["SES_SENDER_EMAIL"],
            Destination={"ToAddresses": [to_email]},
            Message={
                "Subject": {"Data": subject,    "Charset": "UTF-8"},
                "Body": {
                    "Text": {"Data": text_body, "Charset": "UTF-8"},
                    "Html": {"Data": html_body, "Charset": "UTF-8"},
                },
            },
        )
        return True
    except Exception as e:
        logger.error("SES cancellation email failed: %s", str(e))
        return False