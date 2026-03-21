# Using Groq API instead of AWS Bedrock
import json
import logging
import urllib.request
import urllib.error
from flask import current_app

logger = logging.getLogger(__name__)

INTERVIEWER_SYSTEM_PROMPT = """You are an expert technical interviewer conducting a mock walk-in interview.
Ask ONE question at a time. Give feedback after each answer.
After 5-7 questions provide final evaluation EXACTLY like this:
FINAL_SCORE: <number>
FEEDBACK: <paragraph>
STRENGTHS: <bullet points>
IMPROVEMENTS: <bullet points>
Role: {role_title}
JD: {job_description}
"""

GENERAL_INTERVIEWER_PROMPT = """You are an expert technical interviewer.
Ask a mix of technical and behavioural questions one at a time.
After 5-7 questions provide final evaluation EXACTLY like this:
FINAL_SCORE: <number>
FEEDBACK: <paragraph>
STRENGTHS: <bullet points>
IMPROVEMENTS: <bullet points>
"""

def chat_with_interviewer(message, history, role_title=None, job_description=None):
    groq_api_key = current_app.config.get("GROQ_API_KEY")
    if not groq_api_key:
        raise Exception("GROQ_API_KEY not configured")

    system_prompt = INTERVIEWER_SYSTEM_PROMPT.format(
        role_title=role_title or "General",
        job_description=(job_description or "")[:500]
    ) if role_title else GENERAL_INTERVIEWER_PROMPT

    messages = [{"role": "system", "content": system_prompt}]
    for turn in history:
        messages.append({"role": turn.get("role", "user"), "content": turn.get("content", "")})
    messages.append({"role": "user", "content": message})

    payload = json.dumps({
        "model": "llama-3.1-8b-instant",
        "messages": messages,
        "max_tokens": 1024,
        "temperature": 0.7,
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=payload,
        headers={"Authorization": f"Bearer {groq_api_key}", "Content-Type": "application/json"},
        method="POST"
    )

    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read().decode("utf-8"))
        reply_text = result["choices"][0]["message"]["content"].strip()

    is_final = "FINAL_SCORE:" in reply_text
    score = None
    feedback = None

    if is_final:
        for line in reply_text.split("\n"):
            if line.startswith("FINAL_SCORE:"):
                try:
                    score = int(line.split(":")[1].strip())
                except:
                    score = 0
            if line.startswith("FEEDBACK:"):
                feedback = line.split(":", 1)[1].strip()

    return {"reply": reply_text, "is_final": is_final, "score": score, "feedback": feedback}
