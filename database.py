"""SQLite storage and CRUD operations for patient records."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Mapping


DB_PATH = Path(__file__).resolve().parent / "health_prediction.db"
PatientData = Mapping[str, str | float]


class DuplicatePatientError(ValueError):
    """Raised when a patient with the same name and date of birth exists."""


class PatientNotFoundError(LookupError):
    """Raised when an update or delete refers to a missing patient."""


def _is_duplicate_identity_error(error: sqlite3.IntegrityError) -> bool:
    return "patients.full_name, patients.date_of_birth" in str(error)


@contextmanager
def _connection(db_path: str | Path = DB_PATH) -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(str(db_path), timeout=10)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize_database(db_path: str | Path = DB_PATH) -> None:
    """Create the patient table and its duplicate-identity constraint."""
    with _connection(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS patients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL COLLATE NOCASE,
                date_of_birth TEXT NOT NULL,
                email TEXT NOT NULL,
                glucose REAL NOT NULL CHECK (glucose >= 0),
                haemoglobin REAL NOT NULL CHECK (haemoglobin >= 0),
                cholesterol REAL NOT NULL CHECK (cholesterol >= 0),
                remarks TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_patients_unique_identity
            ON patients (full_name COLLATE NOCASE, date_of_birth)
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS validation_issues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                subject TEXT NOT NULL,
                reason TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (source, subject, reason)
            )
            """
        )


def log_validation_issue(
    source: str,
    subject: str,
    reason: str,
    db_path: str | Path = DB_PATH,
) -> None:
    """Record a rejected entry once; repeats of the same rejection are ignored."""
    with _connection(db_path) as connection:
        connection.execute(
            "INSERT OR IGNORE INTO validation_issues (source, subject, reason) VALUES (?, ?, ?)",
            (source, subject, reason),
        )


def count_validation_issues(db_path: str | Path = DB_PATH) -> int:
    """Return the number of distinct rejected entries logged so far."""
    with _connection(db_path) as connection:
        return int(
            connection.execute("SELECT COUNT(*) FROM validation_issues").fetchone()[0]
        )


def _patient_values(patient: PatientData) -> tuple[str | float, ...]:
    return (
        patient["full_name"],
        patient["date_of_birth"],
        patient["email"],
        patient["glucose"],
        patient["haemoglobin"],
        patient["cholesterol"],
        patient["remarks"],
    )


def patient_exists(
    full_name: str,
    date_of_birth: str,
    exclude_id: int | None = None,
    db_path: str | Path = DB_PATH,
) -> bool:
    """Check for another patient with the same case-insensitive name and birth date."""
    query = """
        SELECT 1 FROM patients
        WHERE full_name = ? COLLATE NOCASE AND date_of_birth = ?
    """
    parameters: tuple[str | int, ...] = (full_name, date_of_birth)
    if exclude_id is not None:
        query += " AND id != ?"
        parameters += (exclude_id,)
    with _connection(db_path) as connection:
        return connection.execute(query, parameters).fetchone() is not None


def create_patient(patient: PatientData, db_path: str | Path = DB_PATH) -> int:
    """Insert a patient and return the new record ID."""
    try:
        with _connection(db_path) as connection:
            cursor = connection.execute(
                """
                INSERT INTO patients (
                    full_name, date_of_birth, email, glucose, haemoglobin,
                    cholesterol, remarks
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                _patient_values(patient),
            )
            return int(cursor.lastrowid)
    except sqlite3.IntegrityError as exc:
        if _is_duplicate_identity_error(exc):
            raise DuplicatePatientError(
                "A patient with this full name and date of birth already exists."
            ) from exc
        raise


def list_patients(db_path: str | Path = DB_PATH) -> list[dict[str, object]]:
    """Return all patients, newest record first."""
    with _connection(db_path) as connection:
        rows = connection.execute(
            "SELECT * FROM patients ORDER BY id DESC"
        ).fetchall()
    return [dict(row) for row in rows]


def get_patient(patient_id: int, db_path: str | Path = DB_PATH) -> dict[str, object] | None:
    """Return one patient, or None if that ID does not exist."""
    with _connection(db_path) as connection:
        row = connection.execute(
            "SELECT * FROM patients WHERE id = ?", (patient_id,)
        ).fetchone()
    return dict(row) if row else None


def update_patient(
    patient_id: int,
    patient: PatientData,
    db_path: str | Path = DB_PATH,
) -> None:
    """Update a patient, raising clear errors for duplicates and missing IDs."""
    try:
        with _connection(db_path) as connection:
            cursor = connection.execute(
                """
                UPDATE patients
                SET full_name = ?, date_of_birth = ?, email = ?, glucose = ?,
                    haemoglobin = ?, cholesterol = ?, remarks = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                _patient_values(patient) + (patient_id,),
            )
            if cursor.rowcount == 0:
                raise PatientNotFoundError(f"Patient record {patient_id} was not found.")
    except sqlite3.IntegrityError as exc:
        if _is_duplicate_identity_error(exc):
            raise DuplicatePatientError(
                "A different patient with this full name and date of birth already exists."
            ) from exc
        raise


def delete_patient(patient_id: int, db_path: str | Path = DB_PATH) -> None:
    """Delete one patient by ID."""
    with _connection(db_path) as connection:
        cursor = connection.execute("DELETE FROM patients WHERE id = ?", (patient_id,))
        if cursor.rowcount == 0:
            raise PatientNotFoundError(f"Patient record {patient_id} was not found.")
