# codetext/ignore_logic.py
import os
import re
import logging
from .wildmatch import wildmatch, WM_MATCH, WM_PATHNAME, WM_UNICODE, WM_CASEFOLD

logging.basicConfig(level=logging.WARNING)

class GitIgnorePattern:
    """
    Represents a single .gitignore pattern.
    """
    def __init__(self, pattern: str, source_dir: str, casefold: bool = False) -> None:
        self.original = pattern
        self.source_dir = source_dir
        self.casefold = casefold
        self.negation = pattern.startswith('!')
        if self.negation:
            pattern = pattern[1:]
        self.dir_only = pattern.endswith('/')
        if self.dir_only:
            pattern = pattern.rstrip('/')
        if self.casefold:
            pattern = pattern.lower()
        self.raw_pattern = pattern
        self.regex = None
        self.compile_regex(pattern)

    def compile_regex(self, pattern: str) -> None:
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
        try:
            flag = re.IGNORECASE if self.casefold else 0
            self.regex = re.compile(regex_str, flag)
        except re.error as e:
            logging.warning(f"Regex compilation error for pattern '{pattern}': {e}")
            self.regex = None

    def translate_component(self, component: str) -> str:
        parts = []
        i = 0
        while i < len(component):
            c = component[i]
            if c == '\\':
                if i + 1 < len(component):
                    parts.append(re.escape(component[i + 1]))
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
                    content = component[i + 1 : j]
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

        if '/' not in self.raw_pattern:
            basename = os.path.basename(path)
            flags = WM_UNICODE | WM_PATHNAME
            if self.casefold:
                flags |= WM_CASEFOLD
                basename = basename.lower()
            return wildmatch(self.raw_pattern, basename, flags=flags) == WM_MATCH
        else:
            normalized = '/' + path
            return bool(self.regex and self.regex.fullmatch(normalized))

    def match(self, path: str, is_dir: bool) -> bool:
        return self.hits(path, is_dir) and not self.negation

class GitIgnoreScanner:
    """
    Scans a directory tree using .gitignore patterns.
    """
    def __init__(self, root_dir: str, casefold: bool = False) -> None:
        self.root_dir = os.path.abspath(root_dir)
        self.casefold = casefold
        self.patterns = []

    def load_patterns(self) -> None:
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
        collected.sort(key=lambda x: len(x[0].split('/')) if x[0] else 0, reverse=False)
        self.patterns = []
        for rel_dir, line in collected:
            pat = GitIgnorePattern(line, rel_dir, casefold=self.casefold)
            self.patterns.append(pat)

    def should_ignore(self, path: str, is_dir: bool = False) -> bool:
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
            if pattern.hits(match_path, is_dir):
                result = not pattern.negation
        return result if result is not None else False
