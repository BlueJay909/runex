#!/usr/bin/env python
r"""
Wildmatch Implementation

This module provides a simplified recursive implementation of Git's C wildmatch logic,
which is used for matching shell-style wildcard patterns. It supports common wildcards:
  - '*' matches zero or more characters.
  - '?' matches exactly one character.
  - Bracket expressions (e.g., [abc]) match one character from a set.

It also supports POSIX bracket expressions (e.g., [[:alpha:]]) by mapping them to
equivalent "normal regular expression" character classes. NOTE: collating sequences and
character equivalents are not supported.

A word about POSIX, given the following two definitions:
1 - 'POSIX Character Classes' or 'POSIX Bracket Expression' == ex: [:alnum:]
2 - 'Normal regular expression Character Classes' or 'normal regex Character Sets' == ex: [0-9a-fA-F]

Here is a digression, learned and referenced from "https://www.regular-expressions.info/posixbrackets.html"
that explains how we are going to implement POSIX classes ([:alnum:], [:alpha:], etc.) using only Python's
internally available tools:

"
Generally, only POSIX-compliant regular expression engines have proper and full support for POSIX bracket expressions.
Some non-POSIX regex engines support POSIX character classes, but usually don't support collating sequences and character equivalents.
Regular expression engines that support Unicode use Unicode properties and scripts to provide functionality similar to POSIX bracket expressions.
In Unicode regex engines, shorthand character classes like \w normally match all relevant Unicode characters, alleviating the need to use locales.
"

The way we handle the 'POSIX Character Classes / POSIX Bracket Expressions' in our wildmatch.py implementation,
is by mapping them to equivalent (meaning they match the same thing) 'normal regular expression' character classes.
Those 'normal' character classes ex: [0-9a-fA-F] can then be used in ASCII and Unicode regular expressions
when the POSIX classes are unavailable (and in our case they are unavailable because Python's "re" does not support them).

So, for each 'POSIX class' that we want to support we map _both_ 'an ASCII-only compatible regex character class' and either:
  1 - a Unicode-compatible regex character class,
  2 - a Python shorthand syntax (e.g., \w, \t, \d, \s),
  3 - or a custom function.

This, seems to not make a lot of sense since a lot of the mappings share the same character class for both ascii and unicode,
but i guess it's a cool concept if somebody wants to port all of this in another language.

Flags:
  WM_CASEFOLD  - Enables case-insensitive matching.
  WM_PATHNAME  - Prevents '*' from matching '/', ensuring that wildcards do not cross directory boundaries.
                (Default behavior: Off; however, our core.py explicitly passes WM_PATHNAME to enforce .gitignore rules.)
  WM_UNICODE   - Enables Unicode expansions for POSIX bracket expressions.
                (Default behavior: Off; our core.py explicitly passes WM_UNICODE so that Unicode-aware matching is used.)

Note:
  Although WM_PATHNAME and WM_UNICODE are not enabled by default when calling wildmatch directly with no flags,
  our core.py logic explicitly combines them (i.e., WM_UNICODE | WM_PATHNAME) when performing matching.
  This ensures that our program strictly follows Git's .gitignore rules regarding wildcard and bracket expression behavior.
"""

import re
import unicodedata

# Outcome constants for the matching functions.
WM_ABORT_ALL = -1           # Abort matching entirely.
WM_ABORT_TO_STARSTAR = -2   # Abort due to restrictions from WM_PATHNAME when encountering '/'.
WM_MATCH = 1                # Indicates that the text fully matches the pattern.
WM_NOMATCH = 0              # Indicates that the text does not match the pattern.

# Flag constants that control matching behavior.
WM_CASEFOLD = 1             # When set, matching is case-insensitive.
WM_PATHNAME = 2             # When set, '*' does not match '/' (wildcards will not cross directory boundaries).
WM_UNICODE = 4              # When set, POSIX bracket expressions use Unicode expansions.

# ------------------------------------------------------------------------------
# Custom Unicode-Aware Functions for POSIX Classes
# ------------------------------------------------------------------------------
# These helper functions are used to test individual characters for membership
# in a POSIX class when Unicode mode is enabled. They provide the functionality
# that would otherwise be provided by \p-style regex properties in other languages.
def posix_alpha(ch):
    """Return True if the character is alphabetic (Unicode-aware)."""
    return ch.isalpha()

def posix_cntrl(ch):
    """Return True if the character is a control character."""
    return unicodedata.category(ch) == "Cc"

def posix_lower(ch):
    """Return True if the character is lowercase."""
    return ch.islower()

def posix_print(ch):
    """Return True if the character is printable and not a control character."""
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
# This mapping defines, for each POSIX character class (or bracket expression),
# an ASCII expansion and a Unicode expansion. (see module docstring) The ASCII expansion is a string of
# character ranges that works for ASCII text, while the Unicode expansion is a regex
# shorthand or similar mechanism for Unicode text. For some classes (e.g., 'alpha'),
# the Unicode expansion is None, meaning that a custom function (like posix_alpha) will be used.

#
# NOTE: Collating sequences and character equivalents are not supported.
POSIX_MAPPING = {
    'alnum': ('a-zA-Z0-9', r'\w'),
    'alpha': ('a-zA-Z', None),  # Use custom function posix_alpha for Unicode.
    'ascii': (r'\x00-\x7F', r'\x00-\x7F'),
    'blank': (' \t', ' \t'),
    'cntrl': (r'\x00-\x1F\x7F', None),  # Use posix_cntrl for Unicode.
    'digit': ('0-9', r'\d'),
    'graph': (r'\x21-\x7E', None),
    'lower': ('a-z', None),  # Use posix_lower for Unicode.
    'print': (r'\x20-\x7E', None),  # Use posix_print for Unicode.
    'punct': (r"""!"\#$%&'()*+,\-./:;<=>?@\[\\\]^_`{|}~""", None),  # Use posix_punct for Unicode.
    'space': (' \t\r\n\v\f', r'\s'),
    'upper': ('A-Z', None),  # Use posix_upper for Unicode.
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
    r"""
    Recursively match a wildcard pattern against a given text.

    This function is the core of the wildmatch algorithm. It processes the pattern character by character,
    it supports:
      - Escaping special characters with a '\' to match literals.
      - The '?' wildcard to match any single character (except '/' if WM_PATHNAME is set).
      - The '*' wildcard to match any sequence of characters (unless WM_PATHNAME restricts matching '/').
      - Bracket expressions (e.g., [abc]), including negated expressions ([!abc] or [^abc]).
      - POSIX bracket expressions (e.g., [[:alpha:]]) by expanding them using expand_posix_classes().

    Parameters:
        pattern (str): The wildcard pattern to match (e.g., "*.txt" or "file?[[:digit:]]").
        text (str): The text (often a filename or path) to test against.
        flags (int): Bitwise flags modifying behavior:
                     - WM_CASEFOLD: case-insensitive matching.
                     - WM_PATHNAME: '*' does not match '/'.
                     - WM_UNICODE: use Unicode expansions for POSIX bracket expressions.

    Returns:
        int: WM_MATCH - if the text fully matches the pattern,
             WM_NOMATCH - if it does not match,
             or an abort signal (WM_ABORT_ALL or WM_ABORT_TO_STARSTAR) if matching cannot proceed.
    """
    # If the pattern is anchored (starts with '/'), ensure the text is also anchored.
    if pattern.startswith("/"):
        if not text.startswith("/"):
            return WM_NOMATCH
        # Remove the leading '/' from both pattern and text for further matching.
        pattern = pattern[1:]
        text = text[1:]

    p = 0  # Index in the pattern.
    while p < len(pattern):
        p_ch = pattern[p] if p < len(pattern) else ''

        # If there is no text left but the pattern expects more (except '*' which can match anything), abort.
        if not text and p_ch != '*':
            return WM_ABORT_ALL

        # Apply case-insensitive matching if the WM_CASEFOLD flag is set.
        if flags & WM_CASEFOLD:
            p_ch = p_ch.lower()
            t_ch = text[0].lower() if text else ''
        else:
            t_ch = text[0] if text else ''

        if p_ch == '\\':
            # Handle escaped characters: match the next character literally.
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
            # '*' matches any sequence of characters.
            while p < len(pattern) and pattern[p] == '*':
                p += 1
            if p >= len(pattern):
                # If '*' is the last character, it should match all remaining text.
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
            # Start processing a bracket expression.
            p += 1  # Skip the '['.
            start = p
            while p < len(pattern):
                # Skip nested POSIX expressions if found.
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

            # Check for negation in the bracket expression.
            negated = False
            if bracket_content and bracket_content[0] in ("!", "^"):
                negated = True
                bracket_content = bracket_content[1:]

            # Check if the entire bracket content is a POSIX expression like "[:alpha:]".
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
