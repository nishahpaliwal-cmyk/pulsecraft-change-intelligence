"""Unit tests for pulsecraft.skills.ingest.redaction."""

from __future__ import annotations

from pulsecraft.skills.ingest.redaction import redact


class TestRedactSSN:
    def test_ssn_with_dashes(self) -> None:
        assert "[REDACTED]" in redact("SSN: 123-45-6789")

    def test_ssn_without_dashes(self) -> None:
        assert "[REDACTED]" in redact("SSN:123456789")

    def test_ssn_case_insensitive(self) -> None:
        assert "[REDACTED]" in redact("ssn: 123-45-6789")

    def test_ssn_mixed_case(self) -> None:
        assert "[REDACTED]" in redact("Ssn: 123-45-6789")


class TestRedactDOB:
    def test_dob_slash_format(self) -> None:
        assert "[REDACTED]" in redact("DOB: 1/15/2000")

    def test_dob_two_digit_year(self) -> None:
        assert "[REDACTED]" in redact("DOB:01/15/00")

    def test_dob_case_insensitive(self) -> None:
        assert "[REDACTED]" in redact("dob: 12/31/1999")


class TestRedactMRN:
    def test_mrn_basic(self) -> None:
        assert "[REDACTED]" in redact("MRN: 1234567")

    def test_mrn_no_space(self) -> None:
        assert "[REDACTED]" in redact("MRN:9876543")

    def test_mrn_case_insensitive(self) -> None:
        assert "[REDACTED]" in redact("mrn: 12345")


class TestRedactPassword:
    def test_password_equals(self) -> None:
        assert "[REDACTED]" in redact("password=supersecret")

    def test_password_with_spaces(self) -> None:
        assert "[REDACTED]" in redact("password = hunter2")

    def test_password_case_insensitive(self) -> None:
        assert "[REDACTED]" in redact("PASSWORD=abc123")


class TestRedactAPIKey:
    def test_api_key_colon(self) -> None:
        assert "[REDACTED]" in redact("API_KEY: abc123xyz")

    def test_api_key_equals(self) -> None:
        assert "[REDACTED]" in redact("API_KEY=sk-abcdef")

    def test_api_dash_key(self) -> None:
        assert "[REDACTED]" in redact("API-KEY: some-token")

    def test_apikey_no_separator(self) -> None:
        assert "[REDACTED]" in redact("APIKEY: mytoken")

    def test_api_key_case_insensitive(self) -> None:
        assert "[REDACTED]" in redact("api_key: lowertoken")


class TestRedactEmail:
    def test_simple_email(self) -> None:
        assert "[REDACTED]" in redact("Contact user@example.com for help.")

    def test_email_with_dots(self) -> None:
        assert "[REDACTED]" in redact("first.last@company.org")

    def test_email_with_plus(self) -> None:
        assert "[REDACTED]" in redact("user+tag@mail.example.co.uk")


class TestRedactPhone:
    def test_phone_dashes(self) -> None:
        assert "[REDACTED]" in redact("Call 555-555-1234 for support.")

    def test_phone_dots(self) -> None:
        assert "[REDACTED]" in redact("Phone: 555.555.1234")

    def test_phone_spaces(self) -> None:
        assert "[REDACTED]" in redact("555 555 1234")

    def test_phone_no_separator(self) -> None:
        assert "[REDACTED]" in redact("Phone: 5555551234")


class TestBenignText:
    def test_clean_text_unchanged(self) -> None:
        text = "The order submission API supports batch mode for high-volume workflows."
        assert redact(text) == text

    def test_version_number_not_redacted(self) -> None:
        text = "Version 2.1 is available."
        result = redact(text)
        assert "2.1" in result

    def test_empty_string(self) -> None:
        assert redact("") == ""

    def test_returns_string(self) -> None:
        result = redact("hello world")
        assert isinstance(result, str)

    def test_multiple_patterns_in_one_text(self) -> None:
        text = "SSN: 123-45-6789 and email user@example.com are present."
        result = redact(text)
        assert "123-45-6789" not in result
        assert "@" not in result
        assert "[REDACTED]" in result
