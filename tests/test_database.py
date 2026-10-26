import tempfile
import unittest
from pathlib import Path

from database import (
    DuplicatePatientError,
    PatientNotFoundError,
    count_validation_issues,
    create_patient,
    delete_patient,
    get_patient,
    initialize_database,
    list_patients,
    log_validation_issue,
    update_patient,
)


def sample_patient(**overrides):
    patient = {
        "full_name": "Robyn Pears",
        "date_of_birth": "1960-01-28",
        "email": "robyn@gmail.com",
        "glucose": 232.0,
        "haemoglobin": 13.5,
        "cholesterol": 180.0,
        "remarks": "Informational only; not a medical diagnosis.",
    }
    patient.update(overrides)
    return patient


class PatientDatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test.db"
        initialize_database(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_create_read_update_and_delete(self):
        patient_id = create_patient(sample_patient(), self.db_path)
        saved = get_patient(patient_id, self.db_path)
        self.assertEqual(saved["email"], "robyn@gmail.com")
        self.assertEqual(len(list_patients(self.db_path)), 1)

        update_patient(
            patient_id,
            sample_patient(email="gokul@infocare.com"),
            self.db_path,
        )
        self.assertEqual(
            get_patient(patient_id, self.db_path)["email"], "gokul@infocare.com"
        )

        delete_patient(patient_id, self.db_path)
        self.assertIsNone(get_patient(patient_id, self.db_path))
        self.assertEqual(list_patients(self.db_path), [])

    def test_rejects_duplicate_name_and_birth_date_even_with_different_email(self):
        create_patient(sample_patient(), self.db_path)
        with self.assertRaises(DuplicatePatientError):
            create_patient(
                sample_patient(email="another@example.com"),
                self.db_path,
            )

    def test_validation_issues_are_counted_once_and_do_not_touch_patients(self):
        create_patient(sample_patient(), self.db_path)
        self.assertEqual(count_validation_issues(self.db_path), 0)
        log_validation_issue("Add form", "John Hunter", "Email: invalid", self.db_path)
        log_validation_issue("Add form", "John Hunter", "Email: invalid", self.db_path)
        log_validation_issue("Dataset import", "Peter Larry", "Date: impossible", self.db_path)
        self.assertEqual(count_validation_issues(self.db_path), 2)
        self.assertEqual(len(list_patients(self.db_path)), 1)

    def test_missing_record_updates_and_deletes_raise_clear_errors(self):
        with self.assertRaises(PatientNotFoundError):
            update_patient(99, sample_patient(), self.db_path)
        with self.assertRaises(PatientNotFoundError):
            delete_patient(99, self.db_path)


if __name__ == "__main__":
    unittest.main()
