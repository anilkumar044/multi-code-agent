"""
Comprehensive test suite for the palindrome checker in solution.py.
"""

import pytest
from solution import is_palindrome


# ---------------------------------------------------------------------------
# Normal cases — default (non-strict) mode
# ---------------------------------------------------------------------------

def test_simple_palindrome_returns_true():
    assert is_palindrome("racecar") is True


def test_simple_non_palindrome_returns_false():
    assert is_palindrome("hello") is False


def test_single_character_is_palindrome():
    assert is_palindrome("a") is True


def test_two_same_chars_is_palindrome():
    assert is_palindrome("aa") is True


def test_two_different_chars_not_palindrome():
    assert is_palindrome("ab") is False


def test_even_length_palindrome():
    assert is_palindrome("abba") is True


def test_odd_length_palindrome():
    assert is_palindrome("abcba") is True


# ---------------------------------------------------------------------------
# Case insensitivity (non-strict mode)
# ---------------------------------------------------------------------------

def test_mixed_case_palindrome():
    assert is_palindrome("RaceCar") is True


def test_all_uppercase_palindrome():
    assert is_palindrome("RACECAR") is True


def test_mixed_case_non_palindrome():
    assert is_palindrome("Hello") is False


# ---------------------------------------------------------------------------
# Punctuation and spaces ignored (non-strict mode)
# ---------------------------------------------------------------------------

def test_phrase_with_punctuation_and_spaces():
    assert is_palindrome("A man, a plan, a canal: Panama") is True


def test_phrase_with_question_mark():
    assert is_palindrome("Was it a car or a cat I saw?") is True


def test_phrase_with_apostrophe():
    assert is_palindrome("No 'x' in Nixon") is True


def test_phrase_with_contractions():
    assert is_palindrome("Madam, I'm Adam") is True


def test_string_with_only_spaces():
    # All non-alphanumeric → filtered string is "" → palindrome
    assert is_palindrome("   ") is True


def test_string_with_only_punctuation():
    assert is_palindrome("!!!") is True


def test_string_with_numbers():
    assert is_palindrome("12321") is True


def test_string_with_mixed_alnum():
    assert is_palindrome("A1 1a") is True


# ---------------------------------------------------------------------------
# Edge cases — empty string
# ---------------------------------------------------------------------------

def test_empty_string_is_palindrome():
    # An empty string reads the same forwards and backwards
    assert is_palindrome("") is True


# ---------------------------------------------------------------------------
# Strict mode
# ---------------------------------------------------------------------------

def test_strict_mode_simple_palindrome():
    assert is_palindrome("racecar", strict=True) is True


def test_strict_mode_case_sensitive_not_palindrome():
    assert is_palindrome("RaceCar", strict=True) is False


def test_strict_mode_space_matters():
    # "race car" reversed is "rac ecar" — not equal
    assert is_palindrome("race car", strict=True) is False


def test_strict_mode_empty_string():
    assert is_palindrome("", strict=True) is True


def test_strict_mode_single_char():
    assert is_palindrome("x", strict=True) is True


def test_strict_mode_punctuation_matters():
    # "A man, a plan, a canal: Panama" is NOT a strict palindrome
    assert is_palindrome("A man, a plan, a canal: Panama", strict=True) is False


def test_strict_mode_numeric_palindrome():
    assert is_palindrome("12321", strict=True) is True


def test_strict_mode_non_palindrome_number():
    assert is_palindrome("12345", strict=True) is False


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

def test_raises_type_error_for_integer():
    with pytest.raises(TypeError):
        is_palindrome(12321)  # type: ignore[arg-type]


def test_raises_type_error_for_none():
    with pytest.raises(TypeError):
        is_palindrome(None)  # type: ignore[arg-type]


def test_raises_type_error_for_list():
    with pytest.raises(TypeError):
        is_palindrome(["r", "a", "c", "e", "c", "a", "r"])  # type: ignore[arg-type]


def test_raises_type_error_for_bytes():
    with pytest.raises(TypeError):
        is_palindrome(b"racecar")  # type: ignore[arg-type]


def test_type_error_message_includes_type_name():
    with pytest.raises(TypeError, match="int"):
        is_palindrome(42)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Unicode / special characters
# ---------------------------------------------------------------------------

def test_unicode_palindrome():
    # "level" written with accented characters that are still alphanumeric
    assert is_palindrome("aba") is True


def test_unicode_non_palindrome():
    assert is_palindrome("abc") is False


def test_string_with_emoji_only():
    # Emoji are not alphanumeric → filtered to "" → palindrome
    assert is_palindrome("😀😂") is True


def test_whitespace_only_variants():
    for ws in ["\t", "\n", "\r\n", "  \t  "]:
        assert is_palindrome(ws) is True, f"Failed for {ws!r}"
