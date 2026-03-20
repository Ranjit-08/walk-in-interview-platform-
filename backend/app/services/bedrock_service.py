# app/services/bedrock_service.py
# AWS Bedrock integration for the AI mock interview feature.
# Uses Claude 3 Sonnet via the Bedrock Runtime API.

import json
import logging
import boto3
from flask import current_app

logger = logging.getLogger(__name__)

# ── System prompt templates ─────────────────────────────────────────────────

INTERVIEWER_SYSTEM_PROMPT = """
You are an expert technical interviewer conducting a mock walk-in interview.

Your behaviour:
1. Start by greeting the candidate and asking them to introduce themselves.
2. Ask ONE question at a time. Wait for the answer before asking the next.
3. Ask a mix of: technical questions, behavioural (STAR) questions, and situational questions.
4. After each answer, give brief constructive feedback (1–2 sentences).
5. After 5–7 questions, wrap up with an overall score (0–100) and detailed feedback.

Scoring criteria:
- Technical accuracy (30%)
- Communication clarity (25%)
- Problem-solving approach (25%)
- Confidence and professionalism (20%)

Format your final evaluation exactly like this:
FINAL_SCORE: <number>
FEEDBACK: <paragraph of overall feedback>
STRENGTHS: <bullet points>
IMPROVEMENTS: <bullet points>

Role context: {role_title}
Job description: {job_description}
"""

GENERAL_INTERVIEWER_PROMPT = """
You are an expert technical interviewer conducting a general mock interview.
Ask a mix of technical, behavioural, and situational questions.
Give feedback after each answer. After 5–7 questions, provide a final score (0–100) and detailed feedback.

Format your final evaluation exactly like this:
FINAL_SCORE: <number>
FEEDBACK: <paragraph>
STRENGTHS: <bullet points>
IMPROVEMENTS: <bullet points>
"""


def _get_client():
    return boto3.client(
        "bedrock-runtime",
        region_name=current_app.config["BEDROCK_REGION"]
    )


def chat_with_interviewer(
    message:       str,
    history:       list,
    role_title:    str = None,
    job_description: str = None,
) -> dict:
    """
    Sends a message to the Bedrock Claude model acting as an interviewer.

    Args:
        message:         The candidate's latest message.
        history:         List of { "role": "user"|"assistant", "content": "..." }
        role_title:      Optional job role for context-aware questions.
        job_description: Optional JD for context-aware questions.

    Returns:
        {
            "reply":        str,   # AI interviewer's response
            "is_final":     bool,  # True if interview is complete
            "score":        int,   # Only present when is_final=True
            "feedback":     str,   # Only present when is_final=True
        }
    """
    client   = _get_client()
    model_id = current_app.config["BEDROCK_MODEL_ID"]

    # Choose system prompt based on whether we have job context
    if role_title and job_description:
        system_prompt = INTERVIEWER_SYSTEM_PROMPT.format(
            role_title=role_title,
            job_description=job_description[:1000]  # Truncate to avoid token limits
        )
    else:
        system_prompt = GENERAL_INTERVIEWER_PROMPT

    # Build messages array: history + new user message
    messages = []
    for turn in history:
        messages.append({
            "role":    turn.get("role", "user"),
            "content": [{"type": "text", "text": turn.get("content", "")}]
        })
    messages.append({
        "role":    "user",
        "content": [{"type": "text", "text": message}]
    })

    # Call Bedrock
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens":        1024,
        "system":            system_prompt,
        "messages":          messages,
    })

    response = client.invoke_model(
        modelId     = model_id,
        body        = body,
        contentType = "application/json",
        accept      = "application/json",
    )

    result_body = json.loads(response["body"].read())
    reply_text  = result_body["content"][0]["text"]

    # Detect if the AI has given a final evaluation
    is_final = "FINAL_SCORE:" in reply_text
    score    = None
    feedback = None

    if is_final:
        # Parse the structured final response
        lines = reply_text.split("\n")
        for line in lines:
            if line.startswith("FINAL_SCORE:"):
                try:
                    score = int(line.split(":")[1].strip())
                except (ValueError, IndexError):
                    score = 0
            if line.startswith("FEEDBACK:"):
                feedback = line.split(":", 1)[1].strip()

    return {
        "reply":    reply_text,
        "is_final": is_final,
        "score":    score,
        "feedback": feedback,
    }