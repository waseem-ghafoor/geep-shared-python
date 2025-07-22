import ftfy
import unicodedata
import re
from unidecode import unidecode
from geep_shared_python.logging import log_config
import json
from typing import Literal, Optional

logger = log_config.get_logger_and_add_handler("geep-chat-service", __name__)

# Pattern to find C0 control characters (U+0000-U+001F) excluding common whitespace
# (TAB, LF, CR), DEL (U+007F), and C1 control characters (U+0080-U+009F).
_PROBLEMATIC_CONTROL_CHAR_PATTERN = re.compile(
    r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\x80-\x9f]"
)


def fix_text_encoding_and_normalise(
    text: str,
    perform_ftfy: bool = True,
    unicode_normalisation_form: Optional[Literal["NFC", "NFD", "NFKC", "NFKD"]] = "NFC",
) -> str:
    """
    Fixes common text encoding issues (mojibake) and normalises Unicode text.
    """
    original_text_sample = repr(text[:100])
    current_text = text

    if perform_ftfy:
        try:
            fixed_by_ftfy = ftfy.fix_text(current_text)
            if fixed_by_ftfy != current_text:
                logger.debug(
                    f"Text fixed by ftfy. Original sample: {repr(current_text[:100])}, "
                    f"Fixed sample: {repr(fixed_by_ftfy[:100])}"
                )
            current_text = fixed_by_ftfy
        except Exception as e:
            logger.error(
                f"Error during ftfy.fix_text on sample {repr(current_text[:100])}: {e}. "
                "Proceeding with text before ftfy attempt."
            )

    if unicode_normalisation_form:
        try:
            normalised_text = unicodedata.normalize(
                unicode_normalisation_form, current_text
            )
            if normalised_text != current_text:
                logger.debug(
                    f"Text normalised to {unicode_normalisation_form}. "
                    f"Before (sample): {repr(current_text[:100])}, "
                    f"After (sample): {repr(normalised_text[:100])}"
                )
            current_text = normalised_text
        except Exception as e:
            logger.error(
                f"Error during Unicode normalisation ({unicode_normalisation_form}) "
                f"on sample {repr(current_text[:100])}: {e}. "
                "Proceeding with text before normalisation attempt."
            )

    if repr(current_text[:100]) != original_text_sample:
        logger.debug(
            f"fix_text_encoding_and_normalise result. "
            f"Original sample: {original_text_sample}, "
            f"Final sample: {repr(current_text[:100])}"
        )
    return current_text


def remove_problematic_control_chars(text: str, replacement: str = "") -> str:
    """
    Removes problematic control characters from a string while preserving
    common whitespace (Tab, LF, CR).
    """
    sanitised = _PROBLEMATIC_CONTROL_CHAR_PATTERN.sub(replacement, text)
    if sanitised != text:
        logger.debug(
            f"Removed problematic control characters. "
            f"Original sample: {repr(text[:100])}, "
            f"sanitised sample: {repr(sanitised[:100])}"
        )
    return sanitised


def ensure_json_parsable(text: str) -> str:
    """
    Ensures a string that contains JSON can be successfully parsed with json.loads().
    """
    original_sample = repr(text[:100])

    try:
        json.loads(text)
        return text
    except json.JSONDecodeError:
        sanitised = remove_problematic_control_chars(text)

        sanitised = sanitised.replace("\n", " ").replace("\r", " ")

        if sanitised != text:
            logger.info(
                f"JSON sanitisation applied to malformed JSON. "
                f"Original sample: {original_sample}, "
                f"sanitised sample: {repr(sanitised[:100])}"
            )

        return sanitised


def transliterate_and_force_ascii(text: str) -> str:
    """
    Converts a string to 7-bit ASCII by transliterating with unidecode.
    """
    original_text_sample = repr(text[:100])
    current_text = text

    try:
        transliterated_text = unidecode(current_text)
        if transliterated_text != current_text:
            logger.debug(
                f"Text transliterated by unidecode. "
                f"Before (sample): {repr(current_text[:100])}, "
                f"After (sample): {repr(transliterated_text[:100])}"
            )
        current_text = transliterated_text
    except Exception as e:
        logger.error(
            f"Error during unidecode on sample {repr(current_text[:100])}: {e}. "
            "Proceeding with text before unidecode attempt."
        )

    current_text = remove_problematic_control_chars(current_text)

    ascii_text = current_text.encode("ascii", "ignore").decode("ascii")
    if ascii_text != current_text:
        logger.debug(
            f"Non-ASCII characters removed by encode/decode. "
            f"Before (sample): {repr(current_text[:100])}, "
            f"After (ASCII only, sample): {repr(ascii_text[:100])}"
        )
    current_text = ascii_text

    if repr(current_text[:100]) != original_text_sample:
        logger.debug(
            f"transliterate_and_force_ascii result. Original sample: {original_text_sample}, "
            f"Final sample: {repr(current_text[:100])}"
        )
    return current_text
