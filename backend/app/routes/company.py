# app/routes/company.py — /api/company/*
# Company portal: dashboard, job management, booking overview

from flask import Blueprint, request, g
from app.middleware.auth_middleware import require_auth, require_company
from app.utils.db import execute_one, execute_query, execute_write
from app.utils.response import success, error, not_found, forbidden

company_bp = Blueprint("company", __name__)


def _get_company_id(sub: str) -> int | None:
    """Helper — fetches company DB id from Cognito sub."""
    row = execute_one(
        "SELECT id FROM companies WHERE cognito_sub = :sub",
        {"sub": sub}
    )
    return row["id"] if row else None


@company_bp.route("/dashboard", methods=["GET"])
@require_auth
@require_company
def dashboard():
    """Returns company stats: total jobs, bookings, upcoming interviews."""
    company_id = _get_company_id(g.current_user["sub"])
    if not company_id:
        return error("Company profile not found.", 404)

    stats = execute_one(
        """
        SELECT
            COUNT(DISTINCT j.id)                                AS total_jobs,
            COUNT(DISTINCT CASE WHEN j.status='active'
                  THEN j.id END)                                AS active_jobs,
            COALESCE(SUM(j.booked_slots), 0)                   AS total_bookings,
            COUNT(DISTINCT CASE WHEN j.interview_date >= CURDATE()
                  AND j.status='active' THEN j.id END)         AS upcoming_interviews
        FROM jobs j
        WHERE j.company_id = :cid
        """,
        {"cid": company_id}
    )
    return success(stats)


@company_bp.route("/jobs", methods=["GET"])
@require_auth
@require_company
def list_company_jobs():
    """Lists all jobs posted by this company."""
    company_id = _get_company_id(g.current_user["sub"])
    if not company_id:
        return not_found("Company not found.")

    jobs = execute_query(
        """
        SELECT j.*, COUNT(s.id) AS slot_count
        FROM   jobs j
        LEFT JOIN slots s ON s.job_id = j.id
        WHERE  j.company_id = :cid
        GROUP  BY j.id
        ORDER  BY j.created_at DESC
        """,
        {"cid": company_id}
    )
    return success(jobs)


@company_bp.route("/jobs/<int:job_id>/bookings", methods=["GET"])
@require_auth
@require_company
def list_job_bookings(job_id: int):
    """Lists all bookings for a specific job (company must own the job)."""
    company_id = _get_company_id(g.current_user["sub"])
    if not company_id:
        return not_found("Company not found.")

    # Ownership check
    job = execute_one(
        "SELECT id FROM jobs WHERE id = :jid AND company_id = :cid",
        {"jid": job_id, "cid": company_id}
    )
    if not job:
        return forbidden("You do not have access to this job.")

    bookings = execute_query(
        """
        SELECT b.id, b.status, b.confirmation_code, b.booked_at,
               u.full_name, u.email, u.phone,
               s.start_time, s.end_time
        FROM   bookings b
        JOIN   users u ON u.id = b.user_id
        JOIN   slots s ON s.id = b.slot_id
        WHERE  b.job_id = :jid
        ORDER  BY s.start_time, b.booked_at
        """,
        {"jid": job_id}
    )
    return success(bookings)


@company_bp.route("/jobs/<int:job_id>/status", methods=["PUT"])
@require_auth
@require_company
def update_job_status(job_id: int):
    """Allows company to open, close, or cancel a job posting."""
    company_id = _get_company_id(g.current_user["sub"])
    if not company_id:
        return not_found("Company not found.")

    body   = request.get_json() or {}
    status = body.get("status", "").strip()

    if status not in ("active", "closed", "cancelled"):
        return error("Invalid status. Must be: active, closed, or cancelled.", 422)

    affected = execute_write(
        """
        UPDATE jobs SET status = :status
        WHERE id = :jid AND company_id = :cid
        """,
        {"status": status, "jid": job_id, "cid": company_id}
    )

    if not affected:
        return not_found("Job not found or access denied.")

    return success(message=f"Job status updated to '{status}'.")