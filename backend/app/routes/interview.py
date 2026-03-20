# app/routes/interview.py — /api/interview/*
# AI Mock Interview feature powered by AWS Bedrock

from flask import Blueprint, request, g

from app.middleware.auth_middleware import require_auth
from app.middleware.validation import validate_request, InterviewMessageSchema
from app.services.bedrock_service import chat_with_interviewer
from app.utils.db import execute_one, execute_query, execute_write
from app.utils.response import success, created, error, not_found

import json

interview_bp = Blueprint("interview", __name__)


@interview_bp.route("/start", methods=["POST"])
@require_auth
def start_session():
    """
    Creates a new mock interview session.
    Optionally linked to a real job posting for context-aware questions.
    """
    body   = request.get_json() or {}
    job_id = body.get("job_id")

    user = execute_one(
        "SELECT id FROM users WHERE cognito_sub = :sub",
        {"sub": g.current_user["sub"]}
    )
    if not user:
        return not_found("User not found.")

    # Fetch job context if provided
    job = None
    if job_id:
        job = execute_one(
            "SELECT role_title, job_description FROM jobs WHERE id = :jid",
            {"jid": job_id}
        )

    # Create session record in DB
    session_id = execute_write(
        """
        INSERT INTO interview_sessions (user_id, job_id, session_title, transcript)
        VALUES (:uid, :jid, :title, :transcript)
        """,
        {
            "uid":        user["id"],
            "jid":        job_id,
            "title":      f"Mock Interview — {job['role_title']}" if job else "General Mock Interview",
            "transcript": json.dumps([]),
        }
    )

    # Send the opening message from the AI interviewer
    opening = chat_with_interviewer(
        message      = "Hello, I am ready to start the interview.",
        history      = [],
        role_title   = job["role_title"]    if job else None,
        job_description = job["job_description"] if job else None,
    )

    # Save the opening exchange to transcript
    initial_history = [
        {"role": "user",      "content": "Hello, I am ready to start the interview."},
        {"role": "assistant", "content": opening["reply"]},
    ]
    execute_write(
        "UPDATE interview_sessions SET transcript = :t WHERE id = :id",
        {"t": json.dumps(initial_history), "id": session_id}
    )

    return created({
        "session_id": session_id,
        "reply":      opening["reply"],
        "is_final":   opening["is_final"],
    }, "Mock interview session started.")


@interview_bp.route("/chat", methods=["POST"])
@require_auth
def chat():
    """
    Sends a message to the AI interviewer and gets the next question/feedback.
    """
    data, errs = validate_request(InterviewMessageSchema, request.get_json() or {})
    if errs:
        return error("Validation failed.", 422, errs)

    session_id = data.get("session_id")
    if not session_id:
        return error("session_id is required.", 422)

    user = execute_one(
        "SELECT id FROM users WHERE cognito_sub = :sub",
        {"sub": g.current_user["sub"]}
    )
    if not user:
        return not_found("User not found.")

    # Fetch session + ownership check
    session = execute_one(
        """
        SELECT s.*, j.role_title, j.job_description
        FROM   interview_sessions s
        LEFT JOIN jobs j ON j.id = s.job_id
        WHERE  s.id = :sid AND s.user_id = :uid
        """,
        {"sid": session_id, "uid": user["id"]}
    )
    if not session:
        return not_found("Interview session not found.")

    if session["status"] == "completed":
        return error("This interview session has already ended.", 400)

    # Load existing conversation history from DB
    history = json.loads(session["transcript"] or "[]")

    # Call Bedrock
    result = chat_with_interviewer(
        message         = data["message"],
        history         = history,
        role_title      = session.get("role_title"),
        job_description = session.get("job_description"),
    )

    # Append this exchange to history
    history.append({"role": "user",      "content": data["message"]})
    history.append({"role": "assistant", "content": result["reply"]})

    # Determine new session status
    new_status = "completed" if result["is_final"] else "in_progress"

    # Update session in DB
    execute_write(
        """
        UPDATE interview_sessions
        SET    transcript = :t,
               status     = :status,
               score      = :score,
               feedback   = :feedback,
               ended_at   = IF(:is_final, NOW(), NULL)
        WHERE  id = :sid
        """,
        {
            "t":        json.dumps(history),
            "status":   new_status,
            "score":    result.get("score"),
            "feedback": result.get("feedback"),
            "is_final": result["is_final"],
            "sid":      session_id,
        }
    )

    return success({
        "reply":    result["reply"],
        "is_final": result["is_final"],
        "score":    result.get("score"),
        "feedback": result.get("feedback"),
    })


@interview_bp.route("/sessions", methods=["GET"])
@require_auth
def list_sessions():
    """Returns all mock interview sessions for the current user."""
    user = execute_one(
        "SELECT id FROM users WHERE cognito_sub = :sub",
        {"sub": g.current_user["sub"]}
    )
    if not user:
        return not_found("User not found.")

    sessions = execute_query(
        """
        SELECT s.id, s.session_title, s.score, s.status,
               s.started_at, s.ended_at,
               j.role_title
        FROM   interview_sessions s
        LEFT JOIN jobs j ON j.id = s.job_id
        WHERE  s.user_id = :uid
        ORDER  BY s.started_at DESC
        """,
        {"uid": user["id"]}
    )
    return success(sessions)


@interview_bp.route("/sessions/<int:session_id>", methods=["GET"])
@require_auth
def get_session(session_id: int):
    """Returns full transcript and feedback for a completed session."""
    user = execute_one(
        "SELECT id FROM users WHERE cognito_sub = :sub",
        {"sub": g.current_user["sub"]}
    )
    if not user:
        return not_found("User not found.")

    session = execute_one(
        """
        SELECT s.*, j.role_title
        FROM   interview_sessions s
        LEFT JOIN jobs j ON j.id = s.job_id
        WHERE  s.id = :sid AND s.user_id = :uid
        """,
        {"sid": session_id, "uid": user["id"]}
    )
    if not session:
        return not_found("Session not found.")

    # Parse JSON transcript for frontend
    session["transcript"] = json.loads(session.get("transcript") or "[]")
    return success(session)