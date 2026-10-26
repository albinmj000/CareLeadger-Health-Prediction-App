import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from groq import APIError
from httpx import Request

from ai_service import DEFAULT_MODEL, DISCLAIMER, generate_health_remarks
from validation import ValidatedPatient


class GroqIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.patient = ValidatedPatient(
            full_name="Robyn Pears",
            date_of_birth="1960-01-28",
            email="robyn@gmail.com",
            glucose=232.0,
            haemoglobin=13.5,
            cholesterol=180.0,
        )

    def test_missing_key_returns_explicit_non_diagnostic_fallback(self):
        with patch.dict(os.environ, {"GROQ_API_KEY": ""}, clear=False):
            result = generate_health_remarks(self.patient)
        self.assertFalse(result.used_ai)
        self.assertIn("unavailable", result.remarks.lower())
        self.assertIn("not a medical diagnosis", result.remarks)
        self.assertIn("GROQ_API_KEY", result.error)

    def test_calls_groq_and_appends_non_diagnostic_disclaimer(self):
        response = SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content="Discuss these measurements with a clinician."
                    )
                )
            ]
        )
        client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=unittest.mock.Mock(return_value=response))
            )
        )
        with (
            patch.dict(os.environ, {"GROQ_API_KEY": "test-key"}, clear=False),
            patch("ai_service.Groq", return_value=client) as groq,
        ):
            result = generate_health_remarks(self.patient)

        self.assertTrue(result.used_ai)
        self.assertIn(DISCLAIMER, result.remarks)
        self.assertIn(
            "Values reviewed: glucose 232, haemoglobin 13.5, cholesterol 180.",
            result.remarks,
        )
        self.assertEqual(groq.call_args.kwargs["api_key"], "test-key")
        request = client.chat.completions.create.call_args.kwargs
        self.assertEqual(request["model"], DEFAULT_MODEL)
        self.assertIn("Do not diagnose a disease", request["messages"][0]["content"])
        self.assertIn("Glucose: 232", request["messages"][1]["content"])

    def test_model_disclaimer_is_not_duplicated(self):
        response = SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content=(
                            "Interpretation depends on units. "
                            "This is not a medical diagnosis. Please consult a doctor."
                        )
                    )
                )
            ]
        )
        client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=unittest.mock.Mock(return_value=response))
            )
        )
        with (
            patch.dict(os.environ, {"GROQ_API_KEY": "test-key"}, clear=False),
            patch("ai_service.Groq", return_value=client),
        ):
            result = generate_health_remarks(self.patient)
        self.assertEqual(result.remarks.count("not a medical diagnosis"), 1)
        self.assertTrue(result.remarks.endswith(DISCLAIMER.strip()))

    def test_api_failure_returns_explicit_unavailable_result(self):
        client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(
                    create=unittest.mock.Mock(
                        side_effect=APIError(
                            "connection failed",
                            Request("POST", "https://api.groq.com"),
                            body=None,
                        )
                    )
                )
            )
        )
        with (
            patch.dict(os.environ, {"GROQ_API_KEY": "test-key"}, clear=False),
            patch("ai_service.Groq", return_value=client),
        ):
            result = generate_health_remarks(self.patient)

        self.assertFalse(result.used_ai)
        self.assertIn("APIError", result.error)
        self.assertIn("not a medical diagnosis", result.remarks)


if __name__ == "__main__":
    unittest.main()
