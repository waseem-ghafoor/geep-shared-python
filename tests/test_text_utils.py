import json

import pytest

from geep_shared_python.utils.text_utils import (
    fix_text_encoding_and_normalise,
    remove_problematic_control_chars,
    ensure_json_parsable,
    transliterate_and_force_ascii,
)


@pytest.fixture
def mojibake_text() -> str:
    return (
        "CafÃ© MÃ¼ller Ã± Ã¢ÃªÃ®Ã´Ã» â DÃ¼rÃ¼Åt Ä°Å AdamÄ± "
        + "ResumeÌ with accents like eÌ and aÌ "
        + "Direã§ã£o nã£o pode Aã§ã£o NegÃ³cios "
        + "â\x80\x9cQuoted textâ\x80\x9d"
    )


@pytest.fixture
def control_char_text() -> str:
    return "Hello\x00World\x1FTest\x7F"


@pytest.fixture
def non_ascii_text() -> str:
    return "Café with naïveté and ®™©"


@pytest.fixture
def json_with_newlines() -> str:
    return """{
"response": "Ten, wow! Okay, here we go: \n
**Podcasts:**  \n
1. 'Ologies'...\n
Rest of list...",
"end_conversation": false
}"""


@pytest.fixture
def json_with_controls():
    return '{"response": "Hello\u0000World", "end_conversation": false}'


class TestFixTextEncodingAndNormalise:
    def test_mojibake_correction(self, mojibake_text: str):
        """Test basic mojibake correction functionality."""
        result = fix_text_encoding_and_normalise(mojibake_text)

        # Check parts that are successfully fixed
        assert "Café" in result, "Should fix mojibake characters"
        assert "Müller" in result, "Should fix mojibake characters"

        # Use repr() or literal quotes to check for smart quotes
        assert '"Quoted text"' in result, "Should fix smart quotes"
        # Or an alternative approach:
        assert "Quoted text" in result, "Should contain the quoted text"

        # The Portuguese part check
        assert "Negócios" in result, "Should preserve properly encoded parts"

    def test_different_normalisation_form(self, mojibake_text: str):
        """Test with different Unicode normalisation form."""
        nfc_result = fix_text_encoding_and_normalise(mojibake_text)
        nfkd_result = fix_text_encoding_and_normalise(
            mojibake_text, unicode_normalisation_form="NFKD"
        )
        assert (
            nfkd_result != nfc_result
        ), "Different normalisation forms should produce different results"

    def test_without_ftfy(self, mojibake_text: str):
        """Test behavior when ftfy is disabled."""
        no_ftfy_result = fix_text_encoding_and_normalise(
            mojibake_text, perform_ftfy=False
        )
        assert (
            no_ftfy_result == mojibake_text
        ), "Without ftfy, should return input unchanged"


class TestRemoveProblematicControlChars:
    def test_remove_control_chars(self, control_char_text: str):
        """Test removal of control characters."""
        result = remove_problematic_control_chars(control_char_text)
        assert "\x00" not in result, "Should remove null characters"
        assert "\x1F" not in result, "Should remove unit separator characters"
        assert "\x7F" not in result, "Should remove delete characters"
        assert (
            result == "HelloWorldTest"
        ), "Should produce clean string with controls removed"

    def test_custom_replacement(self, control_char_text: str):
        """Test replacing control chars with custom character."""
        result_with_x = remove_problematic_control_chars(
            control_char_text, replacement="X"
        )
        assert (
            result_with_x == "HelloXWorldXTestX"
        ), "Should replace controls with specified character"

    def test_preserve_whitespace(self):
        """Test preservation of valid whitespace characters."""
        whitespace_text = "Hello\nWorld\tTest"
        result = remove_problematic_control_chars(whitespace_text)
        assert result == whitespace_text, "Should preserve valid whitespace characters"


class TestEnsureJsonParsable:
    def test_valid_json_unchanged(self):
        """Test that valid JSON is returned unchanged."""
        valid_json = '{"key": "value"}'
        result = ensure_json_parsable(valid_json)
        assert result == valid_json, "Valid JSON should be returned unchanged"

    def test_fix_json_with_newlines(self, json_with_newlines: str):
        """Test fixing JSON with unescaped newlines."""
        result = ensure_json_parsable(json_with_newlines)

        # Should now be parsable
        try:
            parsed_json = json.loads(result)
            assert isinstance(parsed_json, dict), "Result should be parsable as JSON"
            assert "response" in parsed_json, "JSON structure should be preserved"
        except json.JSONDecodeError as e:
            pytest.fail(f"JSON parsing failed after sanitisation: {e}")

    def test_fix_json_with_controls(self, json_with_controls: str):
        """Test fixing JSON with control characters."""
        result = ensure_json_parsable(json_with_controls)

        # Should now be parsable
        try:
            parsed_json = json.loads(result)
            assert isinstance(parsed_json, dict), "Result should be parsable as JSON"
            assert "response" in parsed_json, "JSON structure should be preserved"
        except json.JSONDecodeError as e:
            pytest.fail(f"JSON parsing failed after sanitisation: {e}")


class TestTransliterateAndForceAscii:
    def test_remove_accents(self, non_ascii_text: str):
        """Test removal of accented characters."""
        result = transliterate_and_force_ascii(non_ascii_text)
        assert "é" not in result, "Should remove accented characters"
        assert "®" not in result, "Should remove special symbols"
        assert result.isascii(), "Result should be pure ASCII"

    def test_transliteration_quality(self, non_ascii_text: str):
        """Test quality of transliteration."""
        result = transliterate_and_force_ascii(non_ascii_text)
        assert "Cafe" in result, "Should transliterate accented characters properly"
        assert "naive" in result, "Should transliterate accented characters properly"

    def test_ascii_unchanged(self):
        """Test that ASCII text is unchanged."""
        ascii_text = "Hello World 123"
        result = transliterate_and_force_ascii(ascii_text)
        assert result == ascii_text, "ASCII text should be unchanged"
