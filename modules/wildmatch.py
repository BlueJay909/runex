#!/usr/bin/env python
"""
Wildmatch implementation

This module provides a simplified recursive translation of Git's C wildmatch
logic for shell-style wildcard matching. It supports wildcards such as '*', '?'
and bracket expressions (e.g. [abc]). In addition, it now supports POSIX bracket
expressions (e.g. [[:alpha:]]) by expanding them into equivalent character sets.

All patterns—whether containing a leading slash or not—are processed here.
Flags such as WM_CASEFOLD (for case-insensitive matching), WM_PATHNAME (preventing
'*' from matching '/'), and WM_UNICODE (to enable Unicode expansions) modify the behavior.

Leading slashes are handled so that patterns starting with "/" are anchored to the root.
"""

import re

# Outcome constants.
WM_ABORT_ALL = -1           # Abort matching entirely.
WM_ABORT_TO_STARSTAR = -2   # Abort due to slash restrictions.
WM_MATCH = 1                # Successful match.
WM_NOMATCH = 0              # No match.

# Flag constants.
WM_CASEFOLD = 1             # Enables case-insensitive matching.
WM_PATHNAME = 2             # Ensures that '*' does not match '/'
WM_UNICODE = 4              # When set, use Unicode expansions for POSIX bracket expressions

# Mapping for POSIX bracket expressions.
# Each key maps to a tuple: (ASCII expansion, Unicode expansion)
POSIX_MAPPING = {
    'alnum':  ('a-zA-Z0-9', r'\w'),
    'alpha':  ('a-zA-Z',    None),
    'ascii':  (r'\x00-\x7F', r'\x00-\x7F'),
    'blank':  (r' \t',      r'[ \t]'),
    'cntrl':  (r'\x00-\x1F\x7F', None),
    'digit':  ('0-9',      r'\d'),
    'graph':  (r'\x21-\x7E', None),
    'lower':  ('a-z',      None),
    'print':  (r'\x20-\x7E', None),
    'punct':  (r"""!"\#$%&'()*+,\-./:;<=>?@\[\\\]^_`{|}~""", None),
    'space':  (r' \t\r\n\v\f', r'\s'),
    'upper':  ('A-Z',      None),
    'word':   (r'A-Za-z0-9_', r'\w'),
    'xdigit': (r'A-Fa-f0-9', r'A-Fa-f0-9')
}

def expand_posix_classes(content: str, flags: int) -> str:
    """
    Expand POSIX bracket class expressions within the given bracket content.
    
    For example, any occurrence of "[:alpha:]" will be replaced by its expansion.
    If WM_UNICODE is set, the Unicode expansion is used (if available); otherwise,
    the ASCII expansion is used.
    
    Args:
        content: The raw content inside the bracket expression (without '[' and ']').
        flags: The matching flags; WM_UNICODE determines which expansion to use.
        
    Returns:
        The content string with all POSIX bracket expressions replaced.
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
        text: The text (usually a filename or path) to match against.
        flags: Bitwise flags modifying matching behavior (WM_CASEFOLD, WM_PATHNAME, WM_UNICODE).

    Returns:
        WM_MATCH (1) if text matches the pattern, WM_NOMATCH (0) if not,
        or one of the abort signals.
    """
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
            if p >= len(pattern):
                return WM_ABORT_ALL
            negated = False
            if pattern[p] in ('!', '^'):
                negated = True
                p += 1
            start = p
            while p < len(pattern) and pattern[p] != ']':
                p += 1
            if p >= len(pattern):
                return WM_ABORT_ALL
            bracket_content = pattern[start:p]
            p += 1  # Skip ']'.
            expanded = expand_posix_classes(bracket_content, flags)
            if not text:
                return WM_NOMATCH
            t_ch = text[0]
            try:
                class_regex = re.compile(f"^[{expanded}]$")
            except re.error:
                return WM_ABORT_ALL
            matched = bool(class_regex.match(t_ch))
            if matched == negated:
                return WM_NOMATCH
            text = text[1:]
            continue

        else:
            if not text or text[0] != p_ch:
                return WM_NOMATCH
            text = text[1:]
            p += 1
            continue

    return WM_MATCH if not text else WM_NOMATCH

def wildmatch(pattern: str, text: str, flags: int = 0) -> int:
    """
    Wrapper function for dowild.
    
    Args:
        pattern: The wildcard pattern.
        text: The text to test.
        flags: Optional flags (WM_CASEFOLD, WM_PATHNAME, WM_UNICODE).
    
    Returns:
        WM_MATCH if text matches the pattern, otherwise WM_NOMATCH.
    """
    res = dowild(pattern, text, flags)
    return WM_MATCH if res == WM_MATCH else WM_NOMATCH
