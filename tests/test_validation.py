import unittest
from datetime import date

from validation import validate_patient_data


class PatientValidationTests(unittest.TestCase):
    def validate(self, **overrides):
        values = {
            "full_name": "Robyn Pears",
            "date_of_birth": "28/01/1960",
            "email": "robyn@gmail.com",
            "glucose": "232",
            "haemoglobin": "13.5",
            "cholesterol": "180",
            "today": date(2026, 10, 26),
        }
        values.update(overrides)
        return validate_patient_data(**values)

    def test_accepts_requested_slash_date_and_normalizes_it(self):
        patient, errors = self.validate()
        self.assertEqual(errors, {})
        self.assertIsNotNone(patient)
        self.assertEqual(patient.date_of_birth, "1960-01-28")
        self.assertEqual(patient.glucose, 232.0)

    def test_accepts_exact_dot_date_from_assessment_table(self):
        patient, errors = self.validate(date_of_birth="28.01.1960")
        self.assertEqual(errors, {})
        self.assertEqual(patient.date_of_birth, "1960-01-28")

    def test_rejects_mixed_date_separators_and_wrong_order(self):
        for value in ("28.01/1960", "1960-01-28"):
            with self.subTest(value=value):
                patient, errors = self.validate(date_of_birth=value)
                self.assertIsNone(patient)
                self.assertIn("Date of birth", errors)

    def test_rejects_impossible_and_future_dates(self):
        for value in ("31.11.2001", "19.10.2030"):
            with self.subTest(value=value):
                patient, errors = self.validate(date_of_birth=value)
                self.assertIsNone(patient)
                self.assertIn("Date of birth", errors)

    def test_rejects_invalid_email_addresses(self):
        for value in ("hunter@gmail", "Kris.wu.gmail.com", "x@@example.com"):
            with self.subTest(value=value):
                patient, errors = self.validate(email=value)
                self.assertIsNone(patient)
                self.assertIn("Email", errors)

    def test_rejects_non_numeric_infinite_and_negative_results(self):
        for field, value in (
            ("glucose", "high"),
            ("haemoglobin", "nan"),
            ("cholesterol", "-1"),
        ):
            with self.subTest(field=field):
                patient, errors = self.validate(**{field: value})
                self.assertIsNone(patient)
                self.assertIn(field.title(), errors)

    def test_reports_all_field_errors_together(self):
        patient, errors = self.validate(
            full_name=" ",
            date_of_birth="31.11.2001",
            email="invalid",
            glucose="not a number",
            haemoglobin="",
            cholesterol="inf",
        )
        self.assertIsNone(patient)
        self.assertEqual(
            set(errors),
            {"Full name", "Date of birth", "Email", "Glucose", "Haemoglobin", "Cholesterol"},
        )


if __name__ == "__main__":
    unittest.main()
