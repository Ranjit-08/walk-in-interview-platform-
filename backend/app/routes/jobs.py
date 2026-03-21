# app/routes/jobs.py — /api/jobs/*
# Job posting (company) and job browsing (user)

from flask import Blueprint, request, g
from datetime import date

from app.middleware.auth_middleware import require_auth, require_company
from app.middleware.validation import validate_request, JobPostSchema
from app.utils.db import execute_one, execute_query, execute_write
from app.utils.response import success, created, error, not_found, forbidden

jobs_bp = Blueprint("jobs", __name__)


@jobs_bp.route("", methods=["GET"])
def list_jobs():
    """
    Public endpoint — lists all active upcoming jobs.
    Supports query params: ?role=&company=&date=
    """
    role_filter    = request.args.get("role",    "").strip()
    company_filter = request.args.get("company", "").strip()
    date_filter    = request.args.get("date",    "").strip()

    where_clauses = [
        "j.status = 'active'",
        "j.interview_date >= CURDATE()",
    ]
    params = {}

    if role_filter:
        where_clauses.append("j.role_title LIKE :role")
        params["role"] = f"%{role_filter}%"

    if company_filter:
        where_clauses.append("c.company_name LIKE :company")
        params["company"] = f"%{company_filter}%"

    if date_filter:
        where_clauses.append("j.interview_date = :idate")
        params["idate"] = date_filter

    where_sql = " AND ".join(where_clauses)

    jobs = execute_query(
        f"""
        SELECT j.id, j.role_title, j.package_lpa, j.interview_date,
               j.experience_min_yrs, j.experience_max_yrs,
               j.candidates_required, j.booked_slots,
               j.total_slots, j.venue_address,
               c.company_name, c.industry,
               (j.total_slots - j.booked_slots) AS available_slots
        FROM   jobs j
        JOIN   companies c ON c.id = j.company_id
        WHERE  {where_sql}
        ORDER  BY j.interview_date ASC, j.created_at DESC
        """,
        params
    )
    return success(jobs)


@jobs_bp.route("/<int:job_id>", methods=["GET"])
def get_job(job_id: int):
    try:
        job = execute_one(
            """
            SELECT j.*, c.company_name, c.industry, c.website,
                   (j.total_slots - j.booked_slots) AS available_slots
            FROM   jobs j
            JOIN   companies c ON c.id = j.company_id
            WHERE  j.id = :jid
            """,
            {"jid": job_id}
        )

        if not job:
            return not_found("Job not found.")

        job = dict(job)

        slots = execute_query(
            """
            SELECT id, start_time, end_time, capacity,
                   booked_count, status,
                   (capacity - booked_count) AS remaining
            FROM   slots
            WHERE  job_id = :jid
            ORDER  BY start_time
            """,
            {"jid": job_id}
        )

        # ✅ FIX: properly indented function
        def serialize_slot(s):
            s = dict(s)
            if s.get("start_time"):
                s["start_time"] = str(s["start_time"])
            if s.get("end_time"):
                s["end_time"] = str(s["end_time"])
            return s

        # ✅ apply conversion
        slots = [serialize_slot(s) for s in slots]

        job["slots"] = slots
        return success(job)

    except Exception as e:
        import traceback
        print("ERROR:", str(e))
        print(traceback.format_exc())
        return error(str(e), 500)
@jobs_bp.route("", methods=["POST"])
@require_auth
@require_company
def create_job():
    """
    Company posts a new walk-in interview.
    Creates the job + all time slots atomically.
    """
    data, errs = validate_request(JobPostSchema, request.get_json() or {})
    if errs:
        return error("Validation failed.", 422, errs)

    # Validate interview date is in the future
    if data["interview_date"] <= date.today():
        return error("Interview date must be a future date.", 422)

    # Get company id
    company = execute_one(
        "SELECT id FROM companies WHERE cognito_sub = :sub",
        {"sub": g.current_user["sub"]}
    )
    if not company:
        return not_found("Company profile not found.")

    # Calculate total_slots from provided slots
    slots_data   = data.pop("slots")
    total_slots  = sum(s.get("capacity", 1) for s in slots_data)

    # Insert the job
    job_id = execute_write(
        """
        INSERT INTO jobs (
            company_id, role_title, job_description, requirements,
            package_lpa, experience_min_yrs, experience_max_yrs,
            interview_date, venue_address, total_slots, candidates_required
        ) VALUES (
            :company_id, :role_title, :job_description, :requirements,
            :package_lpa, :experience_min_yrs, :experience_max_yrs,
            :interview_date, :venue_address, :total_slots, :candidates_required
        )
        """,
        {
            "company_id":          company["id"],
            "role_title":          data["role_title"],
            "job_description":     data["job_description"],
            "requirements":        data.get("requirements"),
            "package_lpa":         data["package_lpa"],
            "experience_min_yrs":  data["experience_min_yrs"],
            "experience_max_yrs":  data.get("experience_max_yrs"),
            "interview_date":      data["interview_date"],
            "venue_address":       data.get("venue_address"),
            "total_slots":         total_slots,
            "candidates_required": data["candidates_required"],
        }
    )

    # Insert all time slots
    for slot in slots_data:
        execute_write(
            """
            INSERT INTO slots (job_id, start_time, end_time, capacity)
            VALUES (:job_id, :start_time, :end_time, :capacity)
            """,
            {
                "job_id":     job_id,
                "start_time": slot["start_time"],
                "end_time":   slot["end_time"],
                "capacity":   slot.get("capacity", 1),
            }
        )

    return created({"job_id": job_id}, "Job posted successfully.")


@jobs_bp.route("/<int:job_id>", methods=["DELETE"])
@require_auth
@require_company
def delete_job(job_id: int):
    """Soft-deletes a job by setting status to cancelled."""
    company = execute_one(
        "SELECT id FROM companies WHERE cognito_sub = :sub",
        {"sub": g.current_user["sub"]}
    )
    if not company:
        return not_found("Company not found.")

    affected = execute_write(
        """
        UPDATE jobs SET status = 'cancelled'
        WHERE id = :jid AND company_id = :cid
        """,
        {"jid": job_id, "cid": company["id"]}
    )

    if not affected:
        return not_found("Job not found or access denied.")

    return success(message="Job cancelled.")