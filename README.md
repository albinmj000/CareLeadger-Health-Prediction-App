# CareLedger — AI Growth Python Skills (Task 2)

A local Streamlit application for patient records, input validation, SQLite CRUD, and optional informational remarks generated through the Groq API. It is an interview-assessment demo, not a clinical decision-support system.

## Features

- Create, read, update, and delete patient records.
- Store full name, date of birth, email, glucose, haemoglobin, cholesterol, AI remarks, and timestamps in SQLite.
- Validate required fields, email format, date shape, real calendar dates, future dates of birth, and finite non-negative numeric results.
- Accept the requested `DD/MM/YYYY` format and the assessment table's exact `DD.MM.YYYY` format. Dates are stored in ISO `YYYY-MM-DD` form and displayed as `DD/MM/YYYY`; the supplied assessment values are not edited.
- Generate informational remarks from the three blood-test values using a real Groq API request when a key is configured. API errors or a missing key are shown clearly and do not prevent saving a valid record.
- Clearly label remarks as informational, not a confirmed diagnosis. No prediction is medical advice.
- Demonstrate the PDF's exact ten test rows, report validation and duplicate errors, update an email, delete a record, and review the resulting list.
- Keep API keys and local patient data out of Git.

## Requirements

- Python 3.10 or newer
- A Groq API key for live AI-generated remarks (the rest of the application works without one)

## Windows PowerShell setup

Open PowerShell in the project folder and run:

```powershell
cd "C:\Users\SOJI\Desktop\Health Prediction APP"
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
```

Put your own key in `.env`:

```dotenv
GROQ_API_KEY=your_real_groq_api_key
# Optional:
# GROQ_MODEL=openai/gpt-oss-20b
```

Get a key from the Groq Console. Do not paste it into Python files, screenshots, a video, a public issue, or GitHub. The `.env` file is ignored by Git. `.env.example` deliberately contains no key.

Start the app:

```powershell
streamlit run app.py
```

Open the local URL printed by Streamlit (normally `http://localhost:8501`). To run automated tests:

```powershell
python -m unittest discover -s tests -v
```

## Using the application

1. **Dashboard** shows metric cards calculated from the database (total patients, added in the last 7 days, validation issues logged, AI remarks generated), the latest records, and system status.
2. **Add patient** validates the entered fields, requests Groq remarks if configured, then saves the record. A missing key or API failure gives a visible warning and an explicit unavailable remark instead.
3. **Patient records** has search, an AI-remarks filter and sorting, a compact table (remarks truncated), a **View full remarks** expander, and Edit / Delete tabs (delete needs a confirmation tick).
4. **Blood-test charts** shows glucose, haemoglobin and cholesterol per patient from stored data. No ranges, risk scores or diagnoses are applied.
5. **Records preview** displays the supplied test dataset unchanged and validates/imports it with the **Validate and import dataset** button. The results table includes the specific validation errors and duplicate handling.

### Exact assessment data and expected validation

The assessment table's dates are written with dots, even though its validation example specifies `dd/mm/yyyy`. The entry validator accepts either exact, consistently separated format (for example `28.01.1960` or `28/01/1960`) and converts it to the same ISO database date. This compatibility rule keeps the source data unchanged.

On the assessment date in the supplied task (26 October 2026), the expected outcomes when starting with an empty database are:

| Test | Expected outcome | Why |
|---|---|---|
| 1 — Robyn Pears | Valid; saved if the API is unavailable or successful | All supplied fields pass validation. |
| 2 — John Hunter | Rejected | `hunter@gmail` has no complete domain suffix, so it is not accepted as a valid email. |
| 3 — Darryl Tim | Valid; saved if the API is unavailable or successful | All supplied fields pass validation. |
| 4 — Peter Larry | Rejected | `31.11.2001` is not a real calendar date: November has only 30 days. |
| 5 — Sam Kerr | Valid; saved if the API is unavailable or successful | All supplied fields pass validation. |
| 6 — Robyn Pears | Rejected as a duplicate | It repeats test 1. A duplicate is the same case-insensitive full name and date of birth; changing the email does not create a second identity. |
| 7 — Madison XI | Valid; saved if the API is unavailable or successful | All supplied fields pass validation; the numeric values are not modified. |
| 8 — Kris Wu | Rejected | `19.10.2030` is in the future relative to the task date, and `Kris.wu.gmail.com` has no `@` separator. Both errors are reported. |
| 9 — Tenille Singh | Valid; saved if the API is unavailable or successful | All supplied fields pass validation. |
| 10 — Prem Kumar | Valid; saved if the API is unavailable or successful | All supplied fields pass validation. |

Validation errors are shown with field names and explanations. Exact duplicates are rejected both in the interface and by a SQLite unique index, so concurrent submissions cannot silently create a second copy. Updating the existing patient's email is allowed; it does not change the duplicate identity.

## Project structure

```text
app.py                 Streamlit pages, forms, feedback, and assessment workflow
styles.py              Navy/teal theme CSS and card/section helpers
.streamlit/config.toml Streamlit theme settings
database.py            SQLite schema (patients, validation_issues), duplicate rules, CRUD
validation.py          Email, date, and numeric validation
ai_service.py          Groq API request, safety wording, and API-failure handling
tests/                 Offline unit tests for validation, CRUD, and Groq integration
requirements.txt       Python dependencies
.env.example           Safe template for the local API key
.gitignore             Excludes secrets, the local database, and generated files
README.md              Setup, operation, assessment, and publishing instructions
```

The SQLite database `health_prediction.db` is created on first run in the project folder and is excluded from Git. It contains sensitive patient information: use only the supplied synthetic assessment data, keep the database on a trusted machine, and do not publish or email it. This demo has no authentication, encryption, or multi-user access controls and is not suitable for real patient records.

## Simple code walkthrough

- **SQLite / `database.py`:** `initialize_database` creates the table. Dates use a sortable ISO format; the test values are stored as numeric SQLite `REAL` values. All SQL uses placeholders. `create_patient`, `list_patients`/`get_patient`, `update_patient`, and `delete_patient` implement CRUD. A database unique index prevents a duplicate full name and date of birth even if two requests arrive together.
- **Validation / `validation.py`:** `validate_patient_data` checks every field and returns either normalized data or a field-to-error mapping. The date parser rejects impossible calendar dates and future dates. Lab measurements must be finite, numeric, and non-negative.
- **AI / `ai_service.py`:** `generate_health_remarks` reads the key from `.env` via `python-dotenv` and calls Groq's chat-completion API. The prompt asks for cautious context, not a diagnosis. A disclaimer is appended to successful responses. Missing keys and Groq API errors return an explicit unavailable status instead of invented health advice or a false success.
- **Interface / `app.py`:** Streamlit collects form data, shows validation and API feedback, and calls the database functions. It also runs the unmodified assessment rows and displays each row's result.

The measurements have no units or laboratory reference ranges in the task. The AI response must therefore be treated as general information only and should be reviewed by a clinician; it cannot confirm a disease.

## Video demonstration checklist

1. Show the app running and explain that the database is local SQLite and that no real patient data or API key will be shown.
2. Open **Records preview**. Point out that all ten names, dates, email addresses, and measurements match the PDF. Explain that the PDF uses `DD.MM.YYYY` while its validation requirement says `DD/MM/YYYY`; the app accepts both exact forms and normalizes dates only for storage/display.
3. Add or configure a private Groq key in `.env` before recording, then show the app making a real request and saving remarks. Do not reveal the key in the recording. If the service is unavailable, show the clear warning and explain that records can still be saved with an explicit unavailable remark.
4. Process the supplied test rows and explain each rejected row:
   - **Test 2:** `hunter@gmail` lacks a complete domain suffix; email validation rejects it.
   - **Test 4:** `31.11.2001` is impossible because November has 30 days; calendar validation rejects it.
   - **Test 6:** it is the same person and birth date as test 1; duplicate identity rules reject the second record.
   - **Test 8:** the 2030 birth date is future-dated for the task date, and its email has no `@`; both field errors are displayed.
   Mention that tests 1, 3, 5, 7, 9, and 10 are valid. If rerunning the batch in a database that already has those records, they are reported as duplicates rather than inserted again.
5. Open **Patient records** and show the created list.
6. Select a record (for example Robyn Pears), change only its email to `gokul@infocare.com`, save, and show the updated email. Explain that unchanged blood-test values keep their existing remarks.
7. Select one record, confirm the delete checkbox, delete it, and show the updated list after deletion.
8. Walk through `database.py` (schema, uniqueness, parameterized SQL), `validation.py` (format and calendar checks), and `ai_service.py` (Groq request, API failure handling, and non-diagnosis disclaimer).
9. End by showing the source project on GitHub without `.env`, the SQLite database, or any other sensitive file.

## Publish the source to GitHub

Create an empty GitHub repository in your own account, then run these commands from the project folder. Replace the URL with your repository URL:

```powershell
git init
git add -A
git status --short
git check-ignore .env health_prediction.db
git commit -m "Build patient health information assessment app"
git branch -M main
git remote add origin https://github.com/<YOUR-USERNAME>/<YOUR-REPOSITORY>.git
git push -u origin main
```

Before committing, verify that `.env` and `health_prediction.db` are not staged. The `git check-ignore` command confirms that these local files are ignored. Never force-add them. If Git prompts for authentication, use GitHub's supported authentication flow; do not put a password or token in the remote URL or source code.

## Manual submission steps

- Fill in your own candidate information from page 1 of the PDF; it is intentionally not included in this project.
- Create the GitHub repository, publish the source using the steps above, and copy its URL.
- Record the demonstration using the checklist. Check the video for visible secrets before sharing.
- Email your candidate information, repository link, and video to `jobs@gokulinfocare.com`. If the video is too large, upload it to Google Drive, allow access to anyone with the link as instructed by the PDF, and verify that the link opens.
