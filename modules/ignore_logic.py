#!/usr/bin/env python
"""
Implements .gitignore like logic

This module defines classes to represent .gitignore patterns and to scan a
directory tree for files/directories that should be ignored based on these rules.
All wildcard matching for basename-only patterns falls back to wildmatch(),
while slash-containing patterns are compiled into regexes.
"""

import os           # For file system operations.
import re           # For regular expression operations.
import logging      # For logging warnings and errors.
import fnmatch      # For Unix filename pattern matching.
from typing import Optional  # For type hints.
from .wildmatch import wildmatch, WM_MATCH, WM_PATHNAME, WM_UNICODE, WM_CASEFOLD

logging.basicConfig(level=logging.WARNING)

class GitIgnorePattern:
    """
    Represents a single .gitignore pattern.

    The pattern is processed to determine:
      - Negation (if it starts with '!')
      - Directory-only rules (if it ends with '/')
      - A corresponding regex for matching paths (for patterns with a slash).
    For basename-only patterns (without a slash), wildmatch() is used.
    """
    def __init__(self, pattern: str, source_dir: str, casefold: bool = False) -> None:
        self.original = pattern  # Raw pattern as written.
        self.source_dir = source_dir  # Relative directory where this pattern was defined.
        self.casefold = casefold
        self.negation = pattern.startswith('!')
        if self.negation:
            pattern = pattern[1:]
        self.dir_only = pattern.endswith('/')
        if self.dir_only:
            pattern = pattern.rstrip('/')
        # Normalize the pattern if casefold is enabled.
        if self.casefold:
            pattern = pattern.lower()
        self.raw_pattern = pattern
        self.regex: Optional[re.Pattern] = None
        self.compile_regex(pattern)

    def compile_regex(self, pattern: str) -> None:
        """
        Compiles the given pattern into a regex for matching.
        For patterns containing a slash, the method constructs a regex that accounts
        for nested directories.
        """
        if '/' in pattern:
            components = [comp for comp in pattern.split('/') if comp]
            regex_str = "^/" if pattern.startswith("/") else "^(?:.*/)?"
            first = True
            for comp in components:
                if comp == "**":
                    regex_str += ".*"
                else:
                    regex_str += ("" if first else "/") + self.translate_component(comp)
                first = False
            if self.dir_only:
                regex_str += "$"
            else:
                regex_str += r"(?:/.*)?$"
        else:
            regex_str = fnmatch.translate(pattern)
            regex_str = regex_str.replace(r'\Z(?ms)', '')
            regex_str = "^/" + regex_str.lstrip("^")
        try:
            flag = re.IGNORECASE if self.casefold else 0
            self.regex = re.compile(regex_str, flag)
        except re.error as e:
            logging.warning(f"Regex compilation error for pattern '{pattern}': {e}")
            self.regex = None

    def translate_component(self, component: str) -> str:
        """
        Translates a component into its regex equivalent.
        Handles escapes, *, ?, and character classes.
        """
        parts = []
        i = 0
        while i < len(component):
            c = component[i]
            if c == '\\':
                if i + 1 < len(component):
                    parts.append(re.escape(component[i+1]))
                    i += 2
                else:
                    parts.append(re.escape(c))
                    i += 1
            elif c == '*':
                parts.append('[^/]*')
                i += 1
            elif c == '?':
                parts.append('[^/]')
                i += 1
            elif c == '[':
                j = i + 1
                negate = False
                if j < len(component) and component[j] in ('!', '^'):
                    negate = True
                    j += 1
                while j < len(component) and component[j] != ']':
                    j += 1
                if j < len(component):
                    content = component[i+1:j]
                    if negate:
                        content = '^' + content[1:]
                    parts.append(f'[{content}]')
                    i = j + 1
                else:
                    parts.append(re.escape(c))
                    i += 1
            else:
                parts.append(re.escape(c))
                i += 1
        return ''.join(parts)

    def hits(self, path: str, is_dir: bool) -> bool:
        if self.dir_only and not is_dir:
            return False
        # For patterns without a slash, match only against the basename.
        if '/' not in self.raw_pattern:
            basename = os.path.basename(path)
            if self.casefold:
                basename = basename.lower()
            flags = WM_UNICODE
            if self.casefold:
                flags |= WM_CASEFOLD
            return wildmatch(self.raw_pattern, basename, flags=flags) == WM_MATCH
        else:
            normalized = '/' + path
            return bool(self.regex and self.regex.fullmatch(normalized))
    
    def match(self, path: str, is_dir: bool) -> bool:
        """
        Returns whether the pattern matches the given path, taking negation into account.
        """
        return self.hits(path, is_dir) and not self.negation

class GitIgnoreScanner:
    """
    Walks through the directory tree starting at root_dir and determines,
    based on collected .gitignore patterns, whether a file or directory should be ignored.
    """
    def __init__(self, root_dir: str, casefold: bool = False) -> None:
        self.root_dir = os.path.abspath(root_dir)
        self.casefold = casefold
        self.patterns: list[GitIgnorePattern] = []

    def load_patterns(self) -> None:
        """
        Reads .gitignore files in the directory tree and collects patterns.
        Patterns in deeper directories take precedence.
        """
        collected = []
        for dirpath, dirnames, filenames in os.walk(self.root_dir):
            if '.git' in dirnames:
                dirnames.remove('.git')
            if '.gitignore' in filenames:
                file_path = os.path.join(dirpath, '.gitignore')
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    rel_dir = os.path.relpath(dirpath, self.root_dir)
                    if rel_dir == '.':
                        rel_dir = ''
                    for line in f:
                        line = re.sub(r'(?<!\\)#.*', '', line).strip()
                        if line:
                            collected.append((rel_dir, line))
        collected.sort(key=lambda x: len(x[0].split('/')) if x[0] else 0, reverse=True)
        self.patterns = []
        for rel_dir, line in collected:
            pat = GitIgnorePattern(line, rel_dir, casefold=self.casefold)
            self.patterns.append(pat)

    def should_ignore(self, path: str, is_dir: bool = False) -> bool:
        """
        Determines whether the given path should be ignored.
        """
        normalized = path.replace(os.sep, '/').replace('\\', '/')
        result = None
        for pattern in self.patterns:
            match_path = normalized
            if pattern.source_dir:
                prefix = pattern.source_dir.replace('\\', '/') + '/'
                if match_path.startswith(prefix):
                    match_path = match_path[len(prefix):]
                elif match_path == pattern.source_dir.replace('\\', '/'):
                    match_path = ''
                else:
                    continue
                stripped = pattern.original.lstrip("!")
                if '/' not in stripped and '/' in match_path:
                    continue
            if pattern.hits(match_path, is_dir):
                result = not pattern.negation
        return result if result is not None else False
