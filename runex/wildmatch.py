#!/usr/bin/env python
"""
Wildmatch Implementation

This module provides a simplified recursive implementation of Git's C wildmatch logic,
which is used for matching shell-style wildcard patterns. It supports common wildcards:
  - '*' matches zero or more characters.
  - '?' matches exactly one character.
  - Bracket expressions, for example, [abc] match one character from a set.
  
It also supports POSIX bracket expressions (for example, [[:alpha:]]) by mapping them to equivalent 'regex character classes' - NOTE: collating sequences and character equivalents are not supported.


Given the two following definitions:

1 - 'POSIX Character Classes' or 'POSIX Bracket Expression' == ex: [:alnum:]

2 - 'Normal regular expression Character Classes' or 'normal regex Character Sets' == ex: [0-9a-fA-F]

Here is a digression learned and referenced from "https://www.regular-expressions.info/posixbrackets.html" that explains how we are going to implement POSIX classes ( [:alnum:], [:alpha:] etc etc etc) using only python internally available tools:

"
Generally, only POSIX-compliant regular expression engines have proper and full support for POSIX bracket expressions. Some non-POSIX regex engines support POSIX character classes, but usually don’t support collating sequences and character equivalents. Regular expression engines that support Unicode use Unicode properties and scripts to provide functionality similar to POSIX bracket expressions. In Unicode regex engines, shorthand character classes like \w normally match all relevant Unicode characters, alleviating the need to use locales.
"

The way we handle the POSIX Character Classes / POSIX Bracket Expressions in our wildmatch.py implementation is by mapping them to equivalent (meaning they match the same thing) "normal regular expression" character classes. Those can be used in ASCII and Unicode regular expressions when the POSIX classes are unavailable (and in our case they are unavailable because python's "re" does not support them).

So, for each 'POSIX class' we map both an ASCII only compatible 'regex character class' and either: 1 - a Unicode compatible 'regex character class', 2 - 'python shorthand syntax' (\w, \t, \d, \s) or 3 - a custom function.

Flags:
  WM_CASEFOLD  - Enables case-insensitive matching. (Default: matching is case sensitive unless this flag is set.)
  WM_PATHNAME  - Prevents '*' from matching '/', ensuring that wildcards do not cross directory boundaries.
                (Default: '*' will match any character including '/' unless this flag is set.
                 Note: Git itself never exposes this option to the user.)
  WM_UNICODE   - Enables Unicode expansions for POSIX bracket expressions.
                (Default: POSIX bracket expressions are treated in an ASCII way unless this flag is set.)
"""

import re
import unicodedata

# Outcome constants for the matching functions.
WM_ABORT_ALL = -1           # Abort matching entirely.
WM_ABORT_TO_STARSTAR = -2   # Abort due to restrictions from WM_PATHNAME flag when encountering '/'.
WM_MATCH = 1                # Indicates that the text fully matches the pattern.
WM_NOMATCH = 0              # Indicates that the text does not match the pattern.

# Flag constants that control matching behavior.
WM_CASEFOLD = 1             # When set, matching is case-insensitive.
WM_PATHNAME = 2             # When set, '*' does not match the '/' character, so wildcards cannot span directory separators.
WM_UNICODE = 4              # When set, POSIX bracket expressions use Unicode expansions.

# ------------------------------------------------------------------------------
# Custom Unicode-Aware Functions for POSIX Classes
# ------------------------------------------------------------------------------
# These helper functions are used to test individual characters for membership
# in a POSIX class when Unicode mode is enabled. They provide the functionality
# that would otherwise be provided by \p-style regex properties in other languages.

def posix_alpha(ch):
    """Return True if the character is alphabetic (using Unicode rules)."""
    return ch.isalpha()

def posix_cntrl(ch):
    """Return True if the character is a control character."""
    return unicodedata.category(ch) == "Cc"

def posix_lower(ch):
    """Return True if the character is lowercase."""
    return ch.islower()

def posix_print(ch):
    """Return True if the character is printable and is not a control character."""
    return ch.isprintable() and not unicodedata.category(ch).startswith("C")

def posix_punct(ch):
    """Return True if the character is punctuation."""
    return unicodedata.category(ch).startswith("P")

def posix_upper(ch):
    """Return True if the character is uppercase."""
    return ch.isupper()

# ------------------------------------------------------------------------------
# POSIX Bracket Expression Mapping
# ------------------------------------------------------------------------------
# This dictionary maps each POSIX character class (or POSIX bracket expression)
# to two equivalent representations:
#   1. An ASCII expansion: A string of character ranges that works for ASCII text.
#   2. A Unicode expansion: A regex shorthand (or similar) that works for Unicode text.
# For some classes, the Unicode expansion is None, which means we will use a custom
# function (such as posix_alpha) to perform the matching.
#
# Do not confuse the POSIX term “character class” (as used in bracket expressions) with
# the typical regular expression character class (or character set). For example, [x-z0-9]
# is a bracket expression (or POSIX character class), while [0-9a-fA-F] is a normal regex
# character set.
#
# The information in this mapping is based on:
#   https://www.regular-expressions.info/posixbrackets.html
#
# NOTE: We do not support collating sequences and character equivalents.
POSIX_MAPPING = {
    'alnum': ('a-zA-Z0-9', r'\w'),
    'alpha': ('a-zA-Z', None),  # Use custom function posix_alpha in Unicode mode.
    'ascii': (r'\x00-\x7F', r'\x00-\x7F'),
    'blank': (' \t', ' \t'),
    'cntrl': (r'\x00-\x1F\x7F', None),  # Use posix_cntrl in Unicode mode.
    'digit': ('0-9', r'\d'),
    'graph': (r'\x21-\x7E', None),
    'lower': ('a-z', None),  # Use posix_lower in Unicode mode.
    'print': (r'\x20-\x7E', None),  # Use posix_print in Unicode mode.
    'punct': (r"""!"\#$%&'()*+,\-./:;<=>?@\[\\\]^_`{|}~""", None),  # Use posix_punct in Unicode mode.
    'space': (' \t\r\n\v\f', r'\s'),
    'upper': ('A-Z', None),  # Use posix_upper in Unicode mode.
    'word': (r'A-Za-z0-9_', r'\w'),
    'xdigit': (r'A-Fa-f0-9', r'A-Fa-f0-9')
}

def expand_posix_classes(content: str, flags: int) -> str:
    """
    Expand any POSIX bracket class expressions found within the given content.

    This function looks for expressions like "[:alpha:]" inside a bracket expression,
    and replaces them with an equivalent regular expression character set.
    The expansion chosen depends on the flags:
      - If WM_UNICODE is set, the Unicode expansion is used (if available).
      - Otherwise, the ASCII expansion is used.

    Parameters:
        content (str): The inner content of a bracket expression that may contain a POSIX class.
        flags (int): Matching flags (WM_UNICODE, WM_CASEFOLD, etc.)

    Returns:
        str: The expanded character set as a string, ready to be inserted into a regex.
    """
    # Regular expression to locate POSIX expressions like "[:alpha:]"
    pattern = re.compile(r'\[:([a-z]+):\]')

    def repl(match):
        # Extract the class name, e.g., "alpha"
        cls = match.group(1)
        ascii_eq, unicode_eq = POSIX_MAPPING.get(cls, ('', ''))
        # Choose Unicode expansion if WM_UNICODE flag is set and a Unicode expansion is available.
        if flags & WM_UNICODE:
            return unicode_eq if unicode_eq is not None else ascii_eq
        else:
            return ascii_eq

    # Substitute all occurrences with their expansions.
    return pattern.sub(repl, content)

def dowild(pattern: str, text: str, flags: int) -> int:
    """
    Recursively match a wildcard pattern against the given text.

    This function implements the core logic for matching a pattern with wildcards and bracket expressions.
    It supports:
      - Escaping special characters with a backslash (\\).
      - The '?' wildcard which matches any single character (but not '/' if WM_PATHNAME is set).
      - The '*' wildcard which matches any sequence of characters (unless WM_PATHNAME prevents matching '/').
      - Bracket expressions, such as [abc], including negated ones like [!abc] or [^abc].
      - POSIX bracket expressions, like [[:alpha:]], by expanding them using expand_posix_classes().

    Parameters:
        pattern (str): The wildcard pattern (for example, "*.txt" or "file?[[:digit:]]").
        text (str): The text (often a filename or a path) to test against the pattern.
        flags (int): Bitwise flags that modify matching behavior:
                     - WM_CASEFOLD: perform case-insensitive matching.
                     - WM_PATHNAME: do not allow '*' to match '/'.
                     - WM_UNICODE: use Unicode expansions for POSIX bracket expressions.

    Returns:
        int: WM_MATCH if the text fully matches the pattern,
             WM_NOMATCH if it does not match,
             or a special abort value (WM_ABORT_ALL or WM_ABORT_TO_STARSTAR) if matching cannot proceed.
    """
    # If the pattern starts with a '/', then the match is anchored at the beginning of the text.
    if pattern.startswith("/"):
        if not text.startswith("/"):
            return WM_NOMATCH
        # Remove the leading '/' from both pattern and text for further matching.
        pattern = pattern[1:]
        text = text[1:]

    p = 0  # Index in the pattern.
    while p < len(pattern):
        p_ch = pattern[p] if p < len(pattern) else ''

        # If there is no text left but the pattern expects more (except '*' which can match nothing), abort.
        if not text and p_ch != '*':
            return WM_ABORT_ALL

        # Apply case-insensitive matching if the WM_CASEFOLD flag is set.
        if flags & WM_CASEFOLD:
            p_ch = p_ch.lower()
            t_ch = text[0].lower() if text else ''
        else:
            t_ch = text[0] if text else ''

        if p_ch == '\\':
            # Handle escape: the character following '\' is matched literally.
            p += 1
            if p >= len(pattern):
                return WM_NOMATCH
            literal = pattern[p]
            if not text or text[0] != literal:
                return WM_NOMATCH
            text = text[1:]
            p += 1
            continue

        elif p_ch == '?':
            # '?' should match any single character. With WM_PATHNAME set, it will not match '/'.
            if (flags & WM_PATHNAME) and text[0] == '/':
                return WM_NOMATCH
            if not text:
                return WM_NOMATCH
            text = text[1:]
            p += 1
            continue

        elif p_ch == '*':
            # '*' matches any sequence of characters. Consume all consecutive '*' characters.
            while p < len(pattern) and pattern[p] == '*':
                p += 1
            # If '*' is the last pattern character, it should match the rest of the text.
            if p >= len(pattern):
                if (flags & WM_PATHNAME) and '/' in text:
                    return WM_ABORT_TO_STARSTAR
                return WM_MATCH
            # Otherwise, try to match the remaining pattern at every possible position in the text.
            while True:
                res = dowild(pattern[p:], text, flags)
                if res != WM_NOMATCH:
                    if not (flags & WM_PATHNAME) or res != WM_ABORT_TO_STARSTAR:
                        return res
                if not text:
                    break
                if (flags & WM_PATHNAME) and text[0] == '/':
                    return WM_ABORT_TO_STARSTAR
                text = text[1:]
            return WM_ABORT_ALL

        elif p_ch == '[':
            # Start of a bracket expression.
            p += 1  # Skip the '['.
            start = p  # Mark the beginning of the expression.
            while p < len(pattern):
                # If we find a nested POSIX expression like "[:alpha:]", skip it.
                if pattern[p : p + 2] == "[:":
                    idx = pattern.find(":]", p + 2)
                    if idx == -1:
                        p = len(pattern)
                    else:
                        p = idx + 2
                    continue
                elif pattern[p] == ']':
                    break  # End of bracket expression.
                else:
                    p += 1
            # If no closing ']' is found, abort.
            if p >= len(pattern) or pattern[p] != ']':
                return WM_ABORT_ALL
            # Extract the content inside the brackets.
            bracket_content = pattern[start:p]
            p += 1  # Skip the closing ']'

            # Check for negation in the bracket expression (indicated by a leading '!' or '^').
            negated = False
            if bracket_content and bracket_content[0] in ("!", "^"):
                negated = True
                bracket_content = bracket_content[1:]

            # Determine if the entire bracket content is a POSIX bracket expression, e.g., "[:alpha:]".
            m = re.fullmatch(r"\[:([a-z]+):\]", bracket_content, re.IGNORECASE)
            if m and (flags & WM_UNICODE):
                # In Unicode mode, if a custom function is defined for this class, use it.
                cls_key = m.group(1).lower()
                custom_classes = {
                    "alpha": posix_alpha,
                    "cntrl": posix_cntrl,
                    "lower": posix_lower,
                    "print": posix_print,
                    "punct": posix_punct,
                    "upper": posix_upper
                }
                if cls_key in custom_classes:
                    matched = custom_classes[cls_key](text[0])
                else:
                    # If no custom function is available, expand the POSIX class and match using a regex.
                    try:
                        re_flags = re.IGNORECASE if (flags & WM_CASEFOLD) else 0
                        expanded = expand_posix_classes(bracket_content, flags)
                        class_regex = re.compile(f"^[{expanded}]$", re_flags)
                    except re.error:
                        return WM_ABORT_ALL
                    matched = bool(class_regex.fullmatch(text[0]))
            else:
                # For a normal bracket expression, expand any POSIX classes inside.
                expanded = expand_posix_classes(bracket_content, flags)
                if not text:
                    return WM_NOMATCH
                t_ch = text[0]
                try:
                    re_flags = re.IGNORECASE if (flags & WM_CASEFOLD) else 0
                    # Build the regex pattern; if negated, match any character NOT in the set.
                    if negated:
                        regex_pattern = f"^[^{expanded}]$"
                    else:
                        regex_pattern = f"^[{expanded}]$"
                    class_regex = re.compile(regex_pattern, re_flags)
                except re.error:
                    return WM_ABORT_ALL
                matched = bool(class_regex.fullmatch(t_ch))

            if not matched:
                return WM_NOMATCH
            # If the bracket expression matches, consume the matched character.
            text = text[1:]
            continue

        else:
            # For literal characters, require an exact match.
            if not text or t_ch != p_ch:
                return WM_NOMATCH
            text = text[1:]
            p += 1
            continue

    # After processing the entire pattern, a successful match occurs only if all text has been consumed.
    return WM_MATCH if not text else WM_NOMATCH

def wildmatch(pattern: str, text: str, flags: int = 0) -> int:
    """
    A wrapper function that matches a wildcard pattern against text.

    It uses the dowild function to perform the matching, and returns WM_MATCH if the
    pattern matches the text, otherwise WM_NOMATCH.

    Parameters:
        pattern (str): The wildcard pattern to match.
        text (str): The text to match against (e.g., a filename or path).
        flags (int): Flags that modify matching behavior (WM_CASEFOLD, WM_PATHNAME, WM_UNICODE).

    Returns:
        int: WM_MATCH if the text matches the pattern; WM_NOMATCH otherwise.
    """
    res = dowild(pattern, text, flags)
    return WM_MATCH if res == WM_MATCH else WM_NOMATCH
