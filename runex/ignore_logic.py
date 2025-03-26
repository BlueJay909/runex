# runex/ignore_logic.py
"""
This module implements .gitignore-like logic for the Runex project.
It provides classes to parse and process .gitignore patterns, and to
determine if a given file or directory should be ignored based on these rules.

Key classes:
    - GitIgnorePattern: Represents a single pattern from a .gitignore file.
    - GitIgnoreScanner: Walks through a directory tree, collects .gitignore
      patterns, and determines whether files/directories should be ignored.
"""

import os
import re
import logging
from typing import Optional
from .wildmatch import wildmatch, WM_MATCH, WM_PATHNAME, WM_UNICODE, WM_CASEFOLD

# Configure logging to output warnings; helpful for debugging regex issues.
logging.basicConfig(level=logging.WARNING)

class GitIgnorePattern:
    """
    Represents a single .gitignore pattern.

    This class processes a pattern string (from a .gitignore file), taking
    into account negation (starting with '!') and directory-only rules (ending with '/').
    For patterns containing a slash, a regex is compiled to handle nested paths;
    for basename-only patterns (without a slash), a simple wildcard matching is used.
    """

    def __init__(self, pattern: str, source_dir: str, casefold: bool = False) -> None:
        # Save the raw pattern as provided.
        self.original = pattern  
        # The relative directory where this .gitignore file was located.
        self.source_dir = source_dir  
        
        # Store whether matching should be case-insensitive.
        self.casefold = casefold
        
        # Check if the pattern starts with '!', meaning it's a negation.
        self.negation = pattern.startswith('!')
        if self.negation:
            # Remove the '!' so that further processing is simpler.
            pattern = pattern[1:]
        
        # Check if the pattern ends with '/', meaning it applies to directories only.
        self.dir_only = pattern.endswith('/')
        if self.dir_only:
            # Remove trailing '/' for internal processing.
            pattern = pattern.rstrip('/')
        
        # If case-insensitive matching is desired, convert the pattern to lower case.
        if self.casefold:
            pattern = pattern.lower()
        
        # Store the processed pattern.
        self.raw_pattern = pattern
        
        # Initialize the compiled regex variable (used for patterns with a slash).
        self.regex: Optional[re.Pattern] = None
        
        # Compile the regex for the pattern.
        self.compile_regex(pattern)

    def compile_regex(self, pattern: str) -> None:
        """
        Compiles the given pattern into a regex for matching.
        
        For patterns that contain a slash, this method constructs a regex that
        accounts for potential nested directory structures. It builds the regex
        by splitting the pattern on '/', translating each component into a regex,
        and then combining them with proper anchors.
        """
        # Split the pattern into its components (ignoring empty components).
        components = [comp for comp in pattern.split('/') if comp]
        # Start the regex. If the pattern starts with '/', anchor it to the root;
        # otherwise, allow matching after any directory structure.
        regex_str = "^/" if pattern.startswith("/") else "^(?:.*/)?"
        first = True  # Flag to handle whether we're at the first component.
        for comp in components:
            if comp == "**":
                # '**' should match any sequence of characters including directory separators.
                regex_str += ".*"
            else:
                # For normal components, translate them to their regex equivalent.
                # Prepend a "/" if it's not the first component.
                regex_str += ("" if first else "/") + self.translate_component(comp)
            first = False
        # If the pattern is meant for directories only, anchor to the end.
        if self.dir_only:
            regex_str += "$"
        else:
            # Otherwise, allow trailing characters (e.g. additional subdirectories/files).
            regex_str += r"(?:/.*)?$"
        try:
            # Compile the regex with IGNORECASE flag if needed.
            flag = re.IGNORECASE if self.casefold else 0
            self.regex = re.compile(regex_str, flag)
        except re.error as e:
            # Log a warning if regex compilation fails.
            logging.warning(f"Regex compilation error for pattern '{pattern}': {e}")
            self.regex = None

    def translate_component(self, component: str) -> str:
        """
        Translates a single component of a .gitignore pattern into its regex equivalent.
        
        This function processes escape characters, wildcards (* and ?), and character
        classes (e.g., [abc] or [!abc]). The output is a regex snippet that matches the
        component according to gitignore rules.
        """
        parts = []  # List to accumulate parts of the regex.
        i = 0  # Index for iterating through the component.
        while i < len(component):
            c = component[i]
            if c == '\\':
                # Handle escape sequences: if '\' is encountered, escape the next character.
                if i + 1 < len(component):
                    parts.append(re.escape(component[i + 1]))
                    i += 2
                else:
                    parts.append(re.escape(c))
                    i += 1
            elif c == '*':
                # '*' matches any sequence of characters except the directory separator.
                parts.append('[^/]*')
                i += 1
            elif c == '?':
                # '?' matches exactly one character (except a '/').
                parts.append('[^/]')
                i += 1
            elif c == '[':
                # Begin processing a bracket expression.
                j = i + 1
                negate = False
                # Check if the first character inside the brackets is a negation symbol.
                if j < len(component) and component[j] in ('!', '^'):
                    negate = True
                    j += 1
                # Move j to the end of the bracket expression.
                while j < len(component) and component[j] != ']':
                    j += 1
                if j < len(component):
                    # Extract the content within the brackets.
                    content = component[i + 1 : j]
                    if negate:
                        # Adjust content for negation.
                        content = '^' + content[1:]
                    # Append a regex character class.
                    parts.append(f'[{content}]')
                    i = j + 1
                else:
                    # If no closing ']' is found, treat the '[' as a literal.
                    parts.append(re.escape(c))
                    i += 1
            else:
                # For any other character, escape it to match literally.
                parts.append(re.escape(c))
                i += 1
        # Join all parts to form the final regex snippet.
        return ''.join(parts)

    def hits(self, path: str, is_dir: bool) -> bool:
        """
        Determines if the given path matches this pattern.
        
        For patterns that do not include a slash, a simpler matching using wildmatch()
        is used on the file's basename. For patterns that do contain a slash, the full
        (normalized) path (with a leading '/') is matched against the compiled regex.
        
        Args:
            path: The file or directory path (relative to the root of the scan).
            is_dir: Boolean indicating if the path is a directory.
        
        Returns:
            True if the path matches the pattern (and thus should be ignored), False otherwise.
        """
        # If the pattern is for directories only and the path is not a directory, no match.
        if self.dir_only and not is_dir:
            return False

        if '/' not in self.raw_pattern:
            # For basename-only patterns, extract the base name of the path.
            basename = os.path.basename(path)
            flags = WM_UNICODE | WM_PATHNAME
            if self.casefold:
                flags |= WM_CASEFOLD
                basename = basename.lower()
            # Use wildmatch (a custom matching function) to determine if it matches.
            return wildmatch(self.raw_pattern, basename, flags=flags) == WM_MATCH
        else:
            # For patterns with a slash, normalize the path to start with '/'.
            normalized = '/' + path
            # Return whether the compiled regex fully matches the normalized path.
            return bool(self.regex and self.regex.fullmatch(normalized))

    def match(self, path: str, is_dir: bool) -> bool:
        """
        Returns whether the pattern matches the given path.

        Note: This method calls 'hits' and then applies the negation flag.
        Negation (patterns starting with '!') is handled at a higher level in the scanner,
        so here we return the match result only if the pattern is not negated.

        Args:
            path: The path to test (relative to the root).
            is_dir: True if the path is a directory, False otherwise.

        Returns:
            True if the pattern matches and it is not a negation rule; otherwise, False.
        """
        return self.hits(path, is_dir) and not self.negation


class GitIgnoreScanner:
    """
    Walks through the directory tree starting at a specified root directory,
    collects all .gitignore patterns found in that tree, and then uses them to
    determine if specific files or directories should be ignored.

    The scanner reads .gitignore files from multiple levels in the directory tree,
    and sorts the patterns by directory depth so that rules from deeper directories
    (which should override higher-level rules) are applied in the correct order.
    """

    def __init__(self, root_dir: str, casefold: bool = False) -> None:
        # Convert the root directory path to an absolute path.
        self.root_dir = os.path.abspath(root_dir)
        # Whether matching should be case-insensitive.
        self.casefold = casefold
        # List to hold all collected GitIgnorePattern objects.
        self.patterns: list[GitIgnorePattern] = []

    def load_patterns(self) -> None:
        """
        Reads all .gitignore files in the directory tree starting at root_dir
        and collects the patterns defined in them.

        The method walks the directory tree, ignoring any '.git' directories,
        and processes each .gitignore file found. It cleans up the patterns by
        stripping comments and empty lines, then creates a GitIgnorePattern object
        for each non-empty pattern.

        Patterns are sorted in ascending order by their directory depth so that
        patterns in deeper directories (which override higher-level ones) are processed
        in the correct order.
        """
        collected = []
        # Walk the entire directory tree starting at root_dir.
        for dirpath, dirnames, filenames in os.walk(self.root_dir):
            # Skip .git directories to avoid processing internal git files.
            if '.git' in dirnames:
                dirnames.remove('.git')
            if '.gitignore' in filenames:
                file_path = os.path.join(dirpath, '.gitignore')
                # Open each .gitignore file with utf-8 encoding and ignore errors.
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    # Get the path relative to the root.
                    rel_dir = os.path.relpath(dirpath, self.root_dir)
                    # For the root directory, use an empty string.
                    if rel_dir == '.':
                        rel_dir = ''
                    # Process each line in the .gitignore file.
                    for line in f:
                        # Remove inline comments (unless escaped) and whitespace.
                        line = re.sub(r'(?<!\\)#.*', '', line).strip()
                        if line:
                            # Collect the relative directory and the pattern line.
                            collected.append((rel_dir, line))
        # Sort collected patterns based on directory depth (shorter paths first).
        collected.sort(key=lambda x: len(x[0].split('/')) if x[0] else 0, reverse=False)
        self.patterns = []
        # Create GitIgnorePattern objects for each collected pattern.
        for rel_dir, line in collected:
            pat = GitIgnorePattern(line, rel_dir, casefold=self.casefold)
            self.patterns.append(pat)

    def should_ignore(self, path: str, is_dir: bool = False) -> bool:
        """
        Determines whether the given path should be ignored based on the collected
        .gitignore patterns.

        The method normalizes the path to use forward slashes, then iterates over
        the patterns. For each pattern, if the pattern's source directory applies to
        the current path, it is tested. If a pattern matches, its negation flag is taken
        into account. The final result is True if any pattern indicates that the path
        should be ignored, otherwise False.

        Args:
            path: The file or directory path (relative to the root directory).
            is_dir: True if the path is a directory, False otherwise.

        Returns:
            A boolean value indicating whether the path should be ignored.
        """
        # Normalize the path to use '/' as the separator.
        normalized = path.replace(os.sep, '/').replace('\\', '/')
        result = None
        # Evaluate each pattern.
        for pattern in self.patterns:
            match_path = normalized
            # If the pattern was defined in a specific directory, adjust the path accordingly.
            if pattern.source_dir:
                prefix = pattern.source_dir.replace('\\', '/') + '/'
                if match_path.startswith(prefix):
                    # Remove the directory prefix from the path.
                    match_path = match_path[len(prefix):]
                elif match_path == pattern.source_dir.replace('\\', '/'):
                    match_path = ''
                else:
                    # If the path doesn't fall under the pattern's source directory, skip it.
                    continue
            # If the pattern matches the (possibly adjusted) path...
            if pattern.hits(match_path, is_dir):
                # Set the result based on the negation flag.
                result = not pattern.negation
        # If no pattern matched, the file should not be ignored.
        return result if result is not None else False
