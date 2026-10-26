"""Input validation for patient records."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import date, datetime


_DATE_PATTERN = re.compile(r"^\d{2}([/.])\d{2}\1\d{4}$")
_EMAIL_PATTERN = re.compile(
    r"^[A-Z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?"
    r"(?:\.[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?)+$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ValidatedPatient:
    full_name: str
    date_of_birth: str
    email: str
    glucose: float
    haemoglobin: float
    cholesterol: float


def _validated_date(value: str, today: date) -> tuple[str | None, str | None]:
    candidate = value.strip()
    if not _DATE_PATTERN.fullmatch(candidate):
        return None, "Enter a date as DD/MM/YYYY (the source table also uses DD.MM.YYYY)."

    try:
        parsed = datetime.strptime(candidate.replace(".", "/"), "%d/%m/%Y").date()
    except ValueError:
        return None, "Enter a real calendar date; this day, month, and year combination does not exist."

    if parsed.strftime("%d/%m/%Y") != candidate.replace(".", "/"):
        return None, "Enter a date using two-digit day and month and a four-digit year."
    if parsed > today:
        return None, "Date of birth cannot be in the future."
    return parsed.isoformat(), None


def _validated_number(value: str, field_label: str) -> tuple[float | None, str | None]:
    candidate = value.strip()
    if not candidate:
        return None, f"{field_label} is required."
    try:
        number = float(candidate)
    except ValueError:
        return None, f"{field_label} must be a numeric value."
    if not math.isfinite(number):
        return None, f"{field_label} must be a finite numeric value."
    if number < 0:
        return None, f"{field_label} cannot be negative."
    return number, None


def validate_patient_data(
    full_name: str,
    date_of_birth: str,
    email: str,
    glucose: str,
    haemoglobin: str,
    cholesterol: str,
    today: date | None = None,
) -> tuple[ValidatedPatient | None, dict[str, str]]:
    """Return normalized patient data and field-specific validation errors."""
    current_date = today or date.today()
    errors: dict[str, str] = {}

    name = full_name.strip()
    if not name:
        errors["Full name"] = "Full name is required."

    normalized_date, date_error = _validated_date(date_of_birth, current_date)
    if date_error:
        errors["Date of birth"] = date_error

    normalized_email = email.strip()
    if not _EMAIL_PATTERN.fullmatch(normalized_email):
        errors["Email"] = "Enter a valid email address, such as name@example.com."

    glucose_value, glucose_error = _validated_number(glucose, "Glucose")
    if glucose_error:
        errors["Glucose"] = glucose_error

    haemoglobin_value, haemoglobin_error = _validated_number(haemoglobin, "Haemoglobin")
    if haemoglobin_error:
        errors["Haemoglobin"] = haemoglobin_error

    cholesterol_value, cholesterol_error = _validated_number(cholesterol, "Cholesterol")
    if cholesterol_error:
        errors["Cholesterol"] = cholesterol_error

    if errors:
        return None, errors

    return (
        ValidatedPatient(
            full_name=name,
            date_of_birth=normalized_date or "",
            email=normalized_email,
            glucose=glucose_value if glucose_value is not None else 0.0,
            haemoglobin=haemoglobin_value if haemoglobin_value is not None else 0.0,
            cholesterol=cholesterol_value if cholesterol_value is not None else 0.0,
        ),
        {},
    )
