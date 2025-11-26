import os
from typing import List, Dict, Any, Tuple

from dotenv import load_dotenv

import utils
from openai_cli import DASEClient

load_dotenv()

DEFAULT_PROMPT_ID = os.getenv(
    "OPENAI_PROMPT_ID",
    "pmpt_68ed9669d8f88195ab599ab84c53870f0ec675ea9d29fd46",
)

dase_client: DASEClient | None = None
session_log = utils.SessionLog()


def _decode_unicode(text: str) -> str:
    """
    Convert escape sequences such as '\\u2019' into their actual characters
    so Dear PyGui renders them correctly.
    """
    # Only decode when the text actually contains escape sequences; otherwise
    # leave it alone to avoid corrupting already decoded Unicode characters.
    if "\\u" not in text and "\\x" not in text:
        return text
    try:
        return text.encode("utf-8").decode("unicode_escape")
    except UnicodeDecodeError:
        return text


def _normalize_punctuation(text: str) -> str:
    """
    Replace common typographic punctuation with ASCII-friendly equivalents so
    the GUI never shows '?' placeholders from missing glyphs.
    """
    replacements = {
        "\u2018": "'",  # left single quote
        "\u2019": "'",  # right single quote / apostrophe
        "\u201c": '"',  # left double quote
        "\u201d": '"',  # right double quote
        "\u2013": "-",  # en dash
        "\u2014": "-",  # em dash
        "\u2026": "...",  # ellipsis
        "\u00a0": " ",  # non-breaking space
    }
    return "".join(replacements.get(ch, ch) for ch in text)


def reset_session(
    difficulty: str,
    reactions: int,
    company_profile: str,
    company_name: str,
    prompt_id: str | None = None,
) -> None:
    """
    Prepare a new OpenAI session and initialize metadata for logging.
    """
    global dase_client, session_log

    dase_client = DASEClient(
        prompt_id=prompt_id or DEFAULT_PROMPT_ID,
        difficulty=difficulty,
        reactions=str(reactions),
        company_profile=company_profile,
        company_name=company_name,
    )

    session_log = utils.SessionLog()
    session_log.add_metadata("company_name", company_name)
    session_log.add_metadata("difficulty", difficulty)
    session_log.add_metadata("reactions", reactions)
    session_log.add_metadata("model", "OpenAI ChatGPT")


def generate(
    user_input: str,
    company_profile: str,
    log: utils.SessionLog,
) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Send a prompt to the OpenAI client and capture the response.
    Returns the text response and an empty list for compatibility with
    the Gemini interface (which streams raw chunks).
    """
    if dase_client is None:
        raise RuntimeError("OpenAI session is not initialized.")

    log.add_turn("user", user_input)
    response_text = dase_client.send_message(user_input)
    response_text = _normalize_punctuation(_decode_unicode(response_text))
    log.add_turn("model", response_text, [])
    return response_text, []
