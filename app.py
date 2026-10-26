"""CareLedger: a Streamlit dashboard for patient records and informational AI remarks."""

from __future__ import annotations

import os
from datetime import date, datetime, timedelta, timezone
from typing import Any

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from ai_service import DEFAULT_MODEL, generate_health_remarks
from database import (
    DB_PATH,
    DuplicatePatientError,
    PatientNotFoundError,
    count_validation_issues,
    create_patient,
    delete_patient,
    initialize_database,
    list_patients,
    log_validation_issue,
    patient_exists,
    update_patient,
)
from styles import (
    NAVY,
    TEAL,
    brand,
    chip,
    empty_state,
    hero,
    inject_styles,
    kpi_card,
    notice,
    section,
)
from validation import ValidatedPatient, validate_patient_data


load_dotenv()
initialize_database()

st.set_page_config(
    page_title="CareLedger | Health Information",
    page_icon="🩺",
    layout="wide",
)
inject_styles()

ASSESSMENT_ROWS: tuple[dict[str, str], ...] = (
    {"test": "1", "full_name": "Robyn Pears", "date_of_birth": "28.01.1960", "email": "robyn@gmail.com", "glucose": "232", "haemoglobin": "13.5", "cholesterol": "180"},
    {"test": "2", "full_name": "John Hunter", "date_of_birth": "10.12.1990", "email": "hunter@gmail", "glucose": "94", "haemoglobin": "15", "cholesterol": "200"},
    {"test": "3", "full_name": "Darryl Tim", "date_of_birth": "12.11.1993", "email": "timd@smh.com.au", "glucose": "240", "haemoglobin": "18.6", "cholesterol": "326"},
    {"test": "4", "full_name": "Peter Larry", "date_of_birth": "31.11.2001", "email": "Larry@hotmail.com", "glucose": "88", "haemoglobin": "11.5", "cholesterol": "165"},
    {"test": "5", "full_name": "Sam Kerr", "date_of_birth": "09.12.2006", "email": "sam@news.com.au", "glucose": "198", "haemoglobin": "8.9", "cholesterol": "192"},
    {"test": "6", "full_name": "Robyn Pears", "date_of_birth": "28.01.1960", "email": "robyn@gmail.com", "glucose": "232", "haemoglobin": "13.5", "cholesterol": "180"},
    {"test": "7", "full_name": "Madison XI", "date_of_birth": "12.09.1998", "email": "madison@hotmail.com", "glucose": "85", "haemoglobin": "7.6", "cholesterol": "163"},
    {"test": "8", "full_name": "Kris Wu", "date_of_birth": "19.10.2030", "email": "Kris.wu.gmail.com", "glucose": "79", "haemoglobin": "16.5", "cholesterol": "197"},
    {"test": "9", "full_name": "Tenille Singh", "date_of_birth": "30.11.1991", "email": "Tenille@yahoo.com", "glucose": "101", "haemoglobin": "15", "cholesterol": "310"},
    {"test": "10", "full_name": "Prem Kumar", "date_of_birth": "28.04.1990", "email": "prem@telstra.com", "glucose": "155", "haemoglobin": "12.5", "cholesterol": "265"},
)

PAGE_DASHBOARD = "📊 Dashboard"
PAGE_ADD = "➕ Add patient"
PAGE_RECORDS = "🗂️ Patient records"
PAGE_CHARTS = "📈 Blood-test charts"
PAGE_PREVIEW = "🧪 Records preview"
PAGES = (PAGE_DASHBOARD, PAGE_ADD, PAGE_RECORDS, PAGE_CHARTS, PAGE_PREVIEW)

UNAVAILABLE_PREFIX = "AI remarks are unavailable"
RECENT_DAYS = 7
MEASUREMENTS = ("glucose", "haemoglobin", "cholesterol")
CHART_COLOURS = {"glucose": TEAL, "haemoglobin": NAVY, "cholesterol": "#5B8DB8"}


def _patient_mapping(patient: ValidatedPatient, remarks: str) -> dict[str, str | float]:
    return {
        "full_name": patient.full_name,
        "date_of_birth": patient.date_of_birth,
        "email": patient.email,
        "glucose": patient.glucose,
        "haemoglobin": patient.haemoglobin,
        "cholesterol": patient.cholesterol,
        "remarks": remarks,
    }


def _display_date(iso_value: object) -> str:
    return date.fromisoformat(str(iso_value)).strftime("%d/%m/%Y")


def _has_ai_remark(patient: dict[str, object]) -> bool:
    return not str(patient["remarks"]).startswith(UNAVAILABLE_PREFIX)


def _short(text: object, limit: int = 80) -> str:
    value = " ".join(str(text).split())
    return value if len(value) <= limit else value[: limit - 1].rstrip() + "…"


def _added_recently(patient: dict[str, object], days: int = RECENT_DAYS) -> bool:
    try:
        created = datetime.strptime(str(patient["created_at"]), "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return False
    created = created.replace(tzinfo=timezone.utc)
    return created >= datetime.now(timezone.utc) - timedelta(days=days)


def _record_label(patient: dict[str, object]) -> str:
    return f"#{patient['id']} · {patient['full_name']} · {_display_date(patient['date_of_birth'])}"


def _log_rejection(source: str, name: str, dob: str, reason: str) -> None:
    subject = f"{name.strip() or '(no name)'} · {dob.strip() or '(no date)'}"
    log_validation_issue(source, subject, reason)


def _errors_summary(errors: dict[str, str]) -> str:
    return "; ".join(f"{field}: {message}" for field, message in errors.items())


def _show_validation_errors(errors: dict[str, str]) -> None:
    lines = "\n".join(f"- **{field}:** {message}" for field, message in errors.items())
    st.error(f"Please correct the following before saving:\n\n{lines}")


def _patient_fields(prefix: str, patient: dict[str, Any] | None = None) -> dict[str, str]:
    defaults = patient or {}

    def number(field: str) -> str:
        return f"{float(defaults[field]):g}" if field in defaults else ""

    st.markdown("**Patient details**")
    left, middle, right = st.columns(3)
    full_name = left.text_input(
        "Full name",
        value=str(defaults.get("full_name", "")),
        placeholder="First and last name",
        key=f"{prefix}_name",
    )
    date_of_birth = middle.text_input(
        "Date of birth",
        value=_display_date(defaults["date_of_birth"]) if "date_of_birth" in defaults else "",
        placeholder="DD/MM/YYYY",
        help="Use DD/MM/YYYY. DD.MM.YYYY is also accepted. Future dates are rejected.",
        key=f"{prefix}_dob",
    )
    email = right.text_input(
        "Email address",
        value=str(defaults.get("email", "")),
        placeholder="name@domain.com",
        key=f"{prefix}_email",
    )
    st.markdown("**Blood-test results**")
    first, second, third = st.columns(3)
    glucose = first.text_input(
        "Glucose",
        value=number("glucose"),
        placeholder="Numeric value",
        help="Enter a number only. Units are not recorded by this application.",
        key=f"{prefix}_glucose",
    )
    haemoglobin = second.text_input(
        "Haemoglobin",
        value=number("haemoglobin"),
        placeholder="Numeric value",
        key=f"{prefix}_haemoglobin",
    )
    cholesterol = third.text_input(
        "Cholesterol",
        value=number("cholesterol"),
        placeholder="Numeric value",
        key=f"{prefix}_cholesterol",
    )
    return {
        "full_name": full_name,
        "date_of_birth": date_of_birth,
        "email": email,
        "glucose": glucose,
        "haemoglobin": haemoglobin,
        "cholesterol": cholesterol,
    }


def _validated_form(values: dict[str, str]) -> tuple[ValidatedPatient | None, dict[str, str]]:
    return validate_patient_data(
        values["full_name"],
        values["date_of_birth"],
        values["email"],
        values["glucose"],
        values["haemoglobin"],
        values["cholesterol"],
    )


def _table_rows(records: list[dict[str, object]]) -> list[dict[str, object]]:
    return [
        {
            "ID": patient["id"],
            "Patient": patient["full_name"],
            "Date of birth": _display_date(patient["date_of_birth"]),
            "Email": patient["email"],
            "Glucose": f"{float(patient['glucose']):g}",
            "Haemoglobin": f"{float(patient['haemoglobin']):g}",
            "Cholesterol": f"{float(patient['cholesterol']):g}",
            "AI remarks (informational)": _short(patient["remarks"]),
            "Added": str(patient["created_at"])[:10],
        }
        for patient in records
    ]


def _show_table(records: list[dict[str, object]]) -> None:
    height = min(38 * (len(records) + 1) + 3, 440)
    st.dataframe(
        _table_rows(records),
        hide_index=True,
        width="stretch",
        height=height,
        column_config={
            "ID": st.column_config.NumberColumn("ID", width="small"),
            "Patient": st.column_config.TextColumn("Patient", width="medium"),
            "AI remarks (informational)": st.column_config.TextColumn(
                "AI remarks (informational)", width="large"
            ),
        },
    )


def _remarks_viewer(records: list[dict[str, object]], key: str) -> None:
    with st.expander("📄 View full remarks", expanded=False):
        if not records:
            st.caption("No records to show.")
            return
        chosen = st.selectbox("Select a patient", records, format_func=_record_label, key=key)
        st.markdown(
            f"**Glucose** {float(chosen['glucose']):g} · "
            f"**Haemoglobin** {float(chosen['haemoglobin']):g} · "
            f"**Cholesterol** {float(chosen['cholesterol']):g}"
        )
        st.info(str(chosen["remarks"]))
        st.caption("AI remarks are informational only and are not a medical diagnosis.")


def _groq_status() -> tuple[bool, str]:
    configured = bool(os.getenv("GROQ_API_KEY", "").strip())
    model = os.getenv("GROQ_MODEL", "").strip() or DEFAULT_MODEL
    return configured, model


def page_dashboard() -> None:
    hero(
        "CareLedger",
        "Patient records with validated blood-test data and cautious, AI-generated information.",
    )
    records = list_patients()
    recent = sum(1 for patient in records if _added_recently(patient))
    ai_count = sum(1 for patient in records if _has_ai_remark(patient))
    issues = count_validation_issues()

    cols = st.columns(4)
    with cols[0]:
        kpi_card("👥", "Total patients", str(len(records)), "Stored in the local SQLite database")
    with cols[1]:
        kpi_card("🆕", "Recently added", str(recent), f"Records added in the last {RECENT_DAYS} days")
    with cols[2]:
        kpi_card("⚠️", "Validation issues", str(issues), "Distinct rejected entries caught so far")
    with cols[3]:
        kpi_card("🤖", "AI remarks generated", str(ai_count), "Records with a live Groq remark")

    left, right = st.columns([2, 1], gap="large")
    with left:
        section("🕒", "Latest records")
        if records:
            _show_table(records[:5])
        else:
            empty_state(
                "🗂️",
                "No patient records yet",
                "Use Add patient, or import the supplied dataset from Records preview.",
            )
    with right:
        section("⚙️", "System status")
        configured, model = _groq_status()
        st.markdown(
            "**Groq AI service** &nbsp;"
            + chip("Key configured" if configured else "Key missing", configured),
            unsafe_allow_html=True,
        )
        st.caption(f"Model: `{model}`")
        st.caption(f"Database: `{DB_PATH.name}` (local, excluded from Git)")
        notice(
            "AI remarks are informational only and are not a medical diagnosis. "
            "Consult a qualified healthcare professional."
        )


def page_add() -> None:
    hero("Add patient", "Enter a record. Every field is validated before anything is saved.")
    with st.form("add_patient_form"):
        values = _patient_fields("add")
        submitted = st.form_submit_button(
            "💾 Validate and save patient", type="primary", width="stretch"
        )

    if not submitted:
        return
    patient, errors = _validated_form(values)
    if errors:
        _show_validation_errors(errors)
        _log_rejection("Add form", values["full_name"], values["date_of_birth"], _errors_summary(errors))
        return
    if patient is None:
        return
    if patient_exists(patient.full_name, patient.date_of_birth):
        st.error(
            "Duplicate patient: a record with this full name and date of birth already exists."
        )
        _log_rejection(
            "Add form", patient.full_name, values["date_of_birth"],
            "Duplicate: same full name and date of birth",
        )
        return

    with st.spinner("Requesting informational remarks from Groq…"):
        ai_result = generate_health_remarks(patient)
    if ai_result.error:
        st.warning(ai_result.error)
    try:
        record_id = create_patient(_patient_mapping(patient, ai_result.remarks))
    except DuplicatePatientError as exc:
        st.error(str(exc))
        return
    st.success(f"Patient saved successfully (record #{record_id}).")
    st.caption(
        "AI remarks generated." if ai_result.used_ai
        else "Saved with an explicit AI-unavailable remark."
    )
    with st.expander("📄 View saved remarks", expanded=True):
        st.info(ai_result.remarks)


def _filtered_records(records: list[dict[str, object]]) -> list[dict[str, object]]:
    search_col, status_col, sort_col = st.columns([2, 1, 1])
    query = search_col.text_input(
        "🔎 Search", placeholder="Search by name or email", key="records_search"
    ).strip().lower()
    status = status_col.selectbox(
        "AI remarks",
        ("All records", "AI remarks generated", "AI remarks unavailable"),
        key="records_status",
    )
    sort_by = sort_col.selectbox(
        "Sort by",
        ("Newest first", "Oldest first", "Name (A–Z)", "Glucose (high to low)",
         "Haemoglobin (high to low)", "Cholesterol (high to low)"),
        key="records_sort",
    )

    result = [
        patient for patient in records
        if (not query or query in str(patient["full_name"]).lower()
            or query in str(patient["email"]).lower())
        and (status == "All records"
             or (status == "AI remarks generated") == _has_ai_remark(patient))
    ]
    if sort_by == "Oldest first":
        result.sort(key=lambda p: int(p["id"]))
    elif sort_by == "Name (A–Z)":
        result.sort(key=lambda p: str(p["full_name"]).lower())
    elif sort_by != "Newest first":
        field = sort_by.split(" ")[0].lower()
        result.sort(key=lambda p: float(p[field]), reverse=True)
    return result


def _edit_tab(records: list[dict[str, object]]) -> None:
    selected = st.selectbox(
        "Choose a record to edit", records, format_func=_record_label, key="edit_patient_id"
    )
    selected_id = int(selected["id"])
    with st.form(f"edit_patient_form_{selected_id}"):
        values = _patient_fields(f"edit_{selected_id}", selected)
        save_changes = st.form_submit_button("💾 Save changes", type="primary", width="stretch")

    if not save_changes:
        return
    patient, errors = _validated_form(values)
    if errors:
        _show_validation_errors(errors)
        _log_rejection("Edit form", values["full_name"], values["date_of_birth"], _errors_summary(errors))
        return
    if patient is None:
        return
    if patient_exists(patient.full_name, patient.date_of_birth, exclude_id=selected_id):
        st.error("Duplicate patient: another record already has this full name and date of birth.")
        _log_rejection(
            "Edit form", patient.full_name, values["date_of_birth"],
            "Duplicate: same full name and date of birth",
        )
        return

    values_changed = any(
        float(selected[field]) != getattr(patient, field) for field in MEASUREMENTS
    )
    ai_result = None
    remarks = str(selected["remarks"])
    if values_changed:
        with st.spinner("Blood-test values changed; requesting new remarks from Groq…"):
            ai_result = generate_health_remarks(patient)
        remarks = ai_result.remarks
        if ai_result.error:
            st.warning(ai_result.error)
    try:
        update_patient(selected_id, _patient_mapping(patient, remarks))
    except (DuplicatePatientError, PatientNotFoundError) as exc:
        st.error(str(exc))
        return

    message = f"Updated record #{selected_id}."
    if ai_result is not None:
        message += (
            " Remarks were regenerated." if ai_result.used_ai
            else " Blood-test values changed; AI remarks are unavailable."
        )
    st.session_state["patient_records_notice"] = message
    st.rerun()


def _delete_tab(records: list[dict[str, object]]) -> None:
    target = st.selectbox(
        "Choose a record to delete", records, format_func=_record_label, key="delete_patient_id"
    )
    confirm = st.checkbox(
        f"I understand that record #{target['id']} will be permanently deleted.",
        key=f"confirm_patient_delete_{target['id']}",
    )
    if st.button("🗑️ Delete selected patient", disabled=not confirm):
        try:
            delete_patient(int(target["id"]))
        except PatientNotFoundError as exc:
            st.error(str(exc))
            return
        st.session_state["patient_records_notice"] = (
            f"Deleted record #{target['id']}. The updated list is shown above."
        )
        st.rerun()


def page_records() -> None:
    hero("Patient records", "Search, filter, review, update or delete stored records.")
    if "patient_records_notice" in st.session_state:
        st.success(st.session_state.pop("patient_records_notice"))

    records = list_patients()
    if not records:
        empty_state(
            "🗂️", "No patient records yet",
            "Add a patient, or import the supplied dataset from Records preview.",
        )
        return

    section("🔎", "Find records")
    visible = _filtered_records(records)
    st.caption(f"Showing {len(visible)} of {len(records)} record(s). Scroll the table sideways on small screens.")
    if visible:
        _show_table(visible)
    else:
        empty_state("🔍", "No matching records", "Try a different search term or clear the filters.")
    _remarks_viewer(visible, key="view_remarks_id")

    section("🛠️", "Manage records")
    edit_tab, delete_tab = st.tabs(["✏️ Edit patient", "🗑️ Delete patient"])
    with edit_tab:
        _edit_tab(records)
    with delete_tab:
        _delete_tab(records)


def page_charts() -> None:
    hero("Blood-test charts", "Stored glucose, haemoglobin and cholesterol values for each patient.")
    records = list_patients()
    if not records:
        empty_state("📈", "Nothing to chart yet", "Charts appear once patient records have been saved.")
        return

    frame = pd.DataFrame(
        {
            "Patient": [f"{p['full_name']} (#{p['id']})" for p in records],
            "glucose": [float(p["glucose"]) for p in records],
            "haemoglobin": [float(p["haemoglobin"]) for p in records],
            "cholesterol": [float(p["cholesterol"]) for p in records],
        }
    )
    chosen = st.multiselect(
        "Patients to include", frame["Patient"].tolist(), default=frame["Patient"].tolist()
    )
    view = frame[frame["Patient"].isin(chosen)]
    if view.empty:
        empty_state("👆", "No patients selected", "Select at least one patient to see the charts.")
        return

    tabs = st.tabs(["🩸 Glucose", "🧬 Haemoglobin", "🧪 Cholesterol"])
    for tab, measurement in zip(tabs, MEASUREMENTS):
        with tab:
            series = view[measurement]
            stats = st.columns(4)
            stats[0].metric("Patients", len(series))
            stats[1].metric("Average", f"{series.mean():.1f}")
            stats[2].metric("Lowest", f"{series.min():g}")
            stats[3].metric("Highest", f"{series.max():g}")
            st.bar_chart(
                view, x="Patient", y=measurement, color=CHART_COLOURS[measurement],
                y_label=measurement.capitalize(), x_label="",
            )
    notice(
        "Values are shown exactly as stored. Units and reference ranges were not supplied, so "
        "no ranges, risk scores or diagnoses are applied. Informational only; not a medical diagnosis."
    )


def _import_dataset() -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    saved_in_run: set[tuple[str, str]] = set()
    for row in ASSESSMENT_ROWS:
        patient, errors = validate_patient_data(
            row["full_name"], row["date_of_birth"], row["email"],
            row["glucose"], row["haemoglobin"], row["cholesterol"],
        )
        if errors:
            reason = _errors_summary(errors)
            _log_rejection("Dataset import", row["full_name"], row["date_of_birth"], reason)
            results.append({"Test #": row["test"], "Patient": row["full_name"],
                            "Status": "Rejected — validation", "Details": reason})
            continue
        if patient is None:
            raise RuntimeError("Validated patient data was unexpectedly missing.")
        duplicate_note = (
            "A patient with the same full name and date of birth already exists; "
            "email changes do not create a new identity."
        )
        if patient_exists(patient.full_name, patient.date_of_birth):
            # Only a repeat inside this dataset counts as a new issue; re-importing
            # rows that were already saved must not inflate the dashboard figure.
            if (patient.full_name.lower(), patient.date_of_birth) in saved_in_run:
                _log_rejection("Dataset import", row["full_name"], row["date_of_birth"],
                               "Duplicate: same full name and date of birth")
            results.append({"Test #": row["test"], "Patient": row["full_name"],
                            "Status": "Rejected — duplicate", "Details": duplicate_note})
            continue

        ai_result = generate_health_remarks(patient)
        try:
            record_id = create_patient(_patient_mapping(patient, ai_result.remarks))
        except DuplicatePatientError:
            results.append({"Test #": row["test"], "Patient": row["full_name"],
                            "Status": "Rejected — duplicate", "Details": duplicate_note})
            continue
        saved_in_run.add((patient.full_name.lower(), patient.date_of_birth))
        results.append(
            {
                "Test #": row["test"],
                "Patient": row["full_name"],
                "Status": f"Saved — record #{record_id}"
                + ("" if ai_result.used_ai else "; AI unavailable"),
                "Details": ai_result.error or "AI remarks generated successfully.",
            }
        )
    return results


def page_preview() -> None:
    hero("Patient Records Preview", "Review and validate patient records using the supplied test dataset.")
    st.caption("Dates may be entered as DD/MM/YYYY or DD.MM.YYYY and are stored in ISO format.")
    with st.expander("Show the supplied dataset", expanded=True):
        st.dataframe(
            [
                {
                    "Test #": row["test"], "Full name": row["full_name"],
                    "Date of birth": row["date_of_birth"], "Email": row["email"],
                    "Glucose": row["glucose"], "Haemoglobin": row["haemoglobin"],
                    "Cholesterol": row["cholesterol"],
                }
                for row in ASSESSMENT_ROWS
            ],
            hide_index=True,
            width="stretch",
        )
    st.warning(
        "Importing sends each valid row's three blood-test values to Groq when GROQ_API_KEY is "
        "configured. Invalid and duplicate rows are reported and not saved. A missing or failed "
        "API call does not prevent valid records from being saved."
    )
    if st.button("▶️ Validate and import dataset", type="primary"):
        with st.spinner("Validating rows and requesting remarks…"):
            st.session_state["assessment_results"] = _import_dataset()

    results = st.session_state.get("assessment_results")
    if results:
        section("📋", "Import results")
        saved = sum(1 for row in results if row["Status"].startswith("Saved"))
        first, second = st.columns(2)
        first.metric("Saved", saved)
        second.metric("Rejected", len(results) - saved)
        st.dataframe(results, hide_index=True, width="stretch")
        st.caption(
            "Invalid rows are not inserted. A duplicate is the same full name (ignoring case) "
            "plus date of birth."
        )


with st.sidebar:
    brand()
    page = st.radio("Navigate", PAGES, label_visibility="collapsed")
    st.divider()
    st.caption("🔒 Patient data stays in a local SQLite database.")
    st.caption("ℹ️ AI remarks are informational, not a medical diagnosis.")

if page == PAGE_DASHBOARD:
    page_dashboard()
elif page == PAGE_ADD:
    page_add()
elif page == PAGE_RECORDS:
    page_records()
elif page == PAGE_CHARTS:
    page_charts()
else:
    page_preview()
