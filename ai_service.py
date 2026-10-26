"""Groq integration for cautious, informational patient remarks."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

from dotenv import load_dotenv
from groq import APIError, Groq

from validation import ValidatedPatient


DEFAULT_MODEL = "openai/gpt-oss-20b"
DISCLAIMER = (
    " Informational only; this is not a medical diagnosis. "
    "Consult a qualified healthcare professional."
)

_DISCLAIMER_HINTS = (
    "informational only",
    "not a medical diagnosis",
    "not a diagnosis",
    "healthcare professional",
    "healthcare provider",
    "medical professional",
    "consult",
)


def _strip_model_disclaimer(text: str) -> str:
    """Drop disclaimer-style sentences so the single fixed disclaimer is not repeated."""
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    kept = [s for s in sentences if not any(h in s.lower() for h in _DISCLAIMER_HINTS)]
    return " ".join(kept).strip()


@dataclass(frozen=True)
class AIResult:
    remarks: str
    used_ai: bool
    error: str | None = None


def _unavailable_remarks() -> str:
    return (
        "AI remarks are unavailable. No health-risk assessment was produced."
        + DISCLAIMER
    )


def generate_health_remarks(patient: ValidatedPatient) -> AIResult:
    """Request a short, non-diagnostic interpretation from the Groq API."""
    load_dotenv()
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        return AIResult(
            remarks=_unavailable_remarks(),
            used_ai=False,
            error="GROQ_API_KEY is not configured. Add your key to the local .env file.",
        )

    model = os.getenv("GROQ_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    try:
        response = Groq(api_key=api_key).chat.completions.create(
            model=model,
            temperature=0.2,
            max_tokens=1024,
            reasoning_effort="low",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You write concise, professional, plain-language remarks about "
                        "blood-test numbers. Use only the supplied glucose, haemoglobin, "
                        "and cholesterol numbers. A line listing all three values is added "
                        "separately, so do not list them again; quote a number only when "
                        "pointing to one specific value, exactly as given. The units are not "
                        "provided, so never state or assume units. Do not diagnose a "
                        "disease, claim that a person has a condition, assign a disease "
                        "probability or risk score, or imply certainty. Write 2 to 3 short "
                        "sentences in one paragraph, no lists or headings: say that "
                        "interpretation depends on the units, the laboratory's reference "
                        "ranges, and the individual's context, and mention at most one "
                        "neutral point a clinician may wish to review. Do NOT include any "
                        "disclaimer or advice to consult a professional; one is added "
                        "separately. Keep it under 60 words."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Glucose: {patient.glucose:g}; "
                        f"haemoglobin: {patient.haemoglobin:g}; "
                        f"cholesterol: {patient.cholesterol:g}. "
                        "Provide cautious informational remarks."
                    ),
                },
            ],
        )
    except APIError as exc:
        error_type = type(exc).__name__
        return AIResult(
            remarks=_unavailable_remarks(),
            used_ai=False,
            error=f"The Groq API request failed ({error_type}). Check the key and connection, then try again.",
        )

    if not response.choices or not response.choices[0].message.content:
        return AIResult(
            remarks=_unavailable_remarks(),
            used_ai=False,
            error="The Groq API returned an empty response. No health-risk assessment was produced.",
        )

    generated_remarks = _strip_model_disclaimer(response.choices[0].message.content)
    if not generated_remarks:
        return AIResult(
            remarks=_unavailable_remarks(),
            used_ai=False,
            error="The Groq API returned an empty response. No health-risk assessment was produced.",
        )
    values_line = (
        f"Values reviewed: glucose {patient.glucose:g}, "
        f"haemoglobin {patient.haemoglobin:g}, cholesterol {patient.cholesterol:g}. "
    )
    return AIResult(
        remarks=values_line + generated_remarks + DISCLAIMER,
        used_ai=True,
    )
