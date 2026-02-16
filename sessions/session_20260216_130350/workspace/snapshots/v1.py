"""
Palindrome checker module.

A palindrome is a string that reads the same forwards and backwards,
ignoring case and non-alphanumeric characters (by default).
"""


def is_palindrome(s: str, strict: bool = False) -> bool:
    """
    Check if a string is a palindrome.

    By default, ignores case and non-alphanumeric characters (e.g., spaces,
    punctuation), which is the most common real-world interpretation.

    Args:
        s: The string to check.
        strict: If True, perform an exact character-by-character comparison
                (case-sensitive, all characters included). Defaults to False.

    Returns:
        True if the string is a palindrome, False otherwise.

    Raises:
        TypeError: If the input is not a string.

    Examples:
        >>> is_palindrome("racecar")
        True
        >>> is_palindrome("A man, a plan, a canal: Panama")
        True
        >>> is_palindrome("hello")
        False
        >>> is_palindrome("RaceCar", strict=True)
        False
        >>> is_palindrome("RaceCar")
        True
    """
    if not isinstance(s, str):
        raise TypeError(f"Expected str, got {type(s).__name__!r}")

    if strict:
        # Exact comparison: case-sensitive, all characters matter
        return s == s[::-1]

    # Normalise: lowercase and keep only alphanumeric characters
    filtered = "".join(ch.lower() for ch in s if ch.isalnum())
    return filtered == filtered[::-1]


if __name__ == "__main__":
    examples = [
        ("racecar", False),
        ("hello", False),
        ("A man, a plan, a canal: Panama", False),
        ("Was it a car or a cat I saw?", False),
        ("No 'x' in Nixon", False),
        ("Madam, I'm Adam", False),
        ("Not a palindrome", False),
        ("", False),
        ("a", False),
        ("Aa", False),
        # Strict mode examples
        ("racecar", True),
        ("RaceCar", True),
        ("Racecar", True),
    ]

    print("=== Palindrome Checker Demo ===\n")
    for text, strict in examples:
        result = is_palindrome(text, strict=strict)
        mode = "strict" if strict else "normal"
        label = "YES" if result else " NO"
        print(f"[{label}] ({mode:6}) {text!r}")
