#!/usr/bin/env python
"""
Wildmatch implementation

This module provides a simplified recursive translation of Git's C wildmatch
logic for shell-style wildcard matching. It supports wildcards such as '*', '?'
and bracket expressions (e.g. [abc]). In addition, it supports POSIX bracket
expressions (e.g. [[:alpha:]]) by expanding them into equivalent character sets.

Flags:
  WM_CASEFOLD enables case-insensitive matching,
  WM_PATHNAME prevents '*' from matching '/',
  WM_UNICODE enables Unicode expansions for POSIX bracket expressions.

Leading slashes are handled so that patterns starting with "/" are anchored to the root.
"""

import re
import unicodedata

# Outcome constants.
WM_ABORT_ALL = -1           # Abort matching entirely.
WM_ABORT_TO_STARSTAR = -2   # Abort due to slash restrictions.
WM_MATCH = 1                # Successful match.
WM_NOMATCH = 0              # No match.

# Flag constants.
WM_CASEFOLD = 1             # Enables case-insensitive matching.
WM_PATHNAME = 2             # Ensures that '*' does not match '/'
WM_UNICODE = 4              # When set, use Unicode expansions for POSIX bracket expressions


# ----------------------------------------
# Custom Unicode–aware functions for selected POSIX classes.
# ----------------------------------------
def posix_alpha(ch):
    return ch.isalpha()


def posix_cntrl(ch):
    return unicodedata.category(ch) == "Cc"


def posix_lower(ch):
    return ch.islower()


def posix_print(ch):
    return ch.isprintable() and not unicodedata.category(ch).startswith("C")


def posix_punct(ch):
    return unicodedata.category(ch).startswith("P")


def posix_upper(ch):
    return ch.isupper()


# ----------------------------------------
# Mapping for POSIX bracket expressions.
# For classes we handle with custom functions in Unicode mode, we set the Unicode expansion to None.
POSIX_MAPPING = {
    'alnum': ('a-zA-Z0-9', r'\w'),
    'alpha': ('a-zA-Z', None),  # Use posix_alpha in Unicode mode.
    'ascii': (r'\x00-\x7F', r'\x00-\x7F'),
    'blank': (' \t', ' \t'),
    'cntrl': (r'\x00-\x1F\x7F', None),  # Use posix_cntrl.
    'digit': ('0-9', r'\d'),
    'graph': (r'\x21-\x7E', None),
    'lower': ('a-z', None),  # Use posix_lower.
    'print': (r'\x20-\x7E', None),  # Use posix_print.
    'punct': (r"""!"\#$%&'()*+,\-./:;<=>?@\[\\\]^_`{|}~""", None),  # Use posix_punct.
    'space': (' \t\r\n\v\f', r'\s'),
    'upper': ('A-Z', None),  # Use posix_upper.
    'word': (r'A-Za-z0-9_', r'\w'),
    'xdigit': (r'A-Fa-f0-9', r'A-Fa-f0-9')
}


def expand_posix_classes(content: str, flags: int) -> str:
    """
    Expand POSIX bracket class expressions within the given content.

    For example, any occurrence of "[:alpha:]" is replaced by its expansion.
    If WM_UNICODE is set, the Unicode expansion is used if available; otherwise,
    the ASCII expansion is used.
    """
    pattern = re.compile(r'\[:([a-z]+):\]')

    def repl(match):
        cls = match.group(1)
        ascii_eq, unicode_eq = POSIX_MAPPING.get(cls, ('', ''))
        if flags & WM_UNICODE:
            return unicode_eq if unicode_eq is not None else ascii_eq
        else:
            return ascii_eq

    return pattern.sub(repl, content)


def dowild(pattern: str, text: str, flags: int) -> int:
    """
    Recursively matches the wildcard pattern against the text.

    Args:
        pattern: The wildcard pattern (supports *, ?, and bracket expressions,
                 including POSIX bracket expressions like [[:alpha:]]).
        text: The text (usually a filename or path) to match.
        flags: Bitwise flags (WM_CASEFOLD, WM_PATHNAME, WM_UNICODE).

    Returns:
        WM_MATCH if text matches, WM_NOMATCH if not, or an abort signal.
    """
    # Handle leading slash.
    if pattern.startswith("/"):
        if not text.startswith("/"):
            return WM_NOMATCH
        pattern = pattern[1:]
        text = text[1:]

    p = 0
    while p < len(pattern):
        p_ch = pattern[p] if p < len(pattern) else ''

        if not text and p_ch != '*':
            return WM_ABORT_ALL

        if flags & WM_CASEFOLD:
            p_ch = p_ch.lower()
            t_ch = text[0].lower() if text else ''
        else:
            t_ch = text[0] if text else ''

        if p_ch == '\\':
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
            if (flags & WM_PATHNAME) and text[0] == '/':
                return WM_NOMATCH
            if not text:
                return WM_NOMATCH
            text = text[1:]
            p += 1
            continue

        elif p_ch == '*':
            while p < len(pattern) and pattern[p] == '*':
                p += 1
            if p >= len(pattern):
                if (flags & WM_PATHNAME) and '/' in text:
                    return WM_ABORT_TO_STARSTAR
                return WM_MATCH
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
            p += 1  # Skip '['.
            start = p
            while p < len(pattern):
                # If we see a nested POSIX expression, skip it.
                if pattern[p : p + 2] == "[:":
                    idx = pattern.find(":]", p + 2)
                    if idx == -1:
                        p = len(pattern)
                    else:
                        p = idx + 2
                    continue
                elif pattern[p] == ']':
                    break
                else:
                    p += 1
            if p >= len(pattern) or pattern[p] != ']':
                return WM_ABORT_ALL
            bracket_content = pattern[start:p]
            p += 1  # Skip ']'

            # Check for generic negation in bracket expressions (e.g. [!a-z])
            negated = False
            if bracket_content and bracket_content[0] in ("!", "^"):
                negated = True
                bracket_content = bracket_content[1:]

            # Check if the entire bracket_content is a POSIX expression like "[:alpha:]"
            m = re.fullmatch(r"\[:([a-z]+):\]", bracket_content, re.IGNORECASE)
            if m and (flags & WM_UNICODE):
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
                    try:
                        re_flags = re.IGNORECASE if (flags & WM_CASEFOLD) else 0
                        expanded = expand_posix_classes(bracket_content, flags)
                        class_regex = re.compile(f"^[{expanded}]$", re_flags)
                    except re.error:
                        return WM_ABORT_ALL
                    matched = bool(class_regex.fullmatch(text[0]))
            else:
                # For generic bracket expression, expand using our mapping.
                expanded = expand_posix_classes(bracket_content, flags)
                if not text:
                    return WM_NOMATCH
                t_ch = text[0]
                try:
                    re_flags = re.IGNORECASE if (flags & WM_CASEFOLD) else 0
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
            text = text[1:]
            continue

        else:
            if not text or t_ch != p_ch:
                return WM_NOMATCH
            text = text[1:]
            p += 1
            continue
    return WM_MATCH if not text else WM_NOMATCH


def wildmatch(pattern: str, text: str, flags: int = 0) -> int:
    res = dowild(pattern, text, flags)
    return WM_MATCH if res == WM_MATCH else WM_NOMATCH
