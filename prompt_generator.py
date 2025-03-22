#!/usr/bin/env python
"""
Main Prompt Generator - Generates Folder structure and appends file contents

This script builds a textual representation of a project's folder structure
and appends the contents of files (excluding those ignored by .gitignore rules)
to generate a complete project prompt.
"""

import os
import argparse
from typing import Optional
from modules.ignore_logic import GitIgnoreScanner

def build_tree(root_dir: str, prefix: str = "", scanner: Optional[GitIgnoreScanner] = None, parent_path: str = "") -> list:
    """
    Recursively builds a list of strings representing the folder structure.
    """
    if scanner is None:
        scanner = GitIgnoreScanner(root_dir, casefold=args.casefold)
        scanner.load_patterns()

    items = []
    full_path = os.path.join(root_dir, parent_path)
    try:
        for name in sorted([x for x in os.listdir(full_path) if x != '.git']):
            items.append((name, os.path.isdir(os.path.join(full_path, name))))
    except PermissionError:
        return []

    filtered = []
    for name, is_dir in items:
        rel_path = os.path.join(parent_path, name) if parent_path else name
        if scanner.should_ignore(rel_path, is_dir):
            continue
        filtered.append((name, is_dir))

    lines = []
    for i, (name, is_dir) in enumerate(filtered):
        connector = "└── " if i == len(filtered) - 1 else "├── "
        line = f"{prefix}{connector}{name}{'/' if is_dir else ''}"
        lines.append(line)
        if is_dir:
            ext = "    " if i == len(filtered) - 1 else "│   "
            lines += build_tree(root_dir, prefix + ext, scanner, os.path.join(parent_path, name))
    return lines

def generate_folder_structure(root_dir: str, casefold: bool) -> str:
    """
    Generates a string representing the folder structure.
    """
    base = os.path.basename(root_dir)
    scanner = GitIgnoreScanner(root_dir, casefold=casefold)
    scanner.load_patterns()
    lines = [f"{base}/"]
    lines += build_tree(root_dir, scanner=scanner)
    return '\n'.join(lines)

def append_file_contents(root_dir: str, casefold: bool) -> str:
    """
    Appends the contents of all non-ignored files (except .gitignore) in the project.
    """
    scanner = GitIgnoreScanner(root_dir, casefold=casefold)
    scanner.load_patterns()
    contents = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        if '.git' in dirnames:
            dirnames.remove('.git')
        rel_dir = os.path.relpath(dirpath, root_dir)
        if rel_dir == '.':
            rel_dir = ''
        dirnames[:] = [d for d in dirnames if not scanner.should_ignore(os.path.join(rel_dir, d), True)]
        for filename in sorted(filenames):
            if filename == ".gitignore":
                continue
            rel_path = os.path.join(rel_dir, filename) if rel_dir else filename
            if scanner.should_ignore(rel_path, False):
                continue
            full_path = os.path.join(dirpath, filename)
            contents.append(f"\n# File: {filename}")
            contents.append(f"# Path: {rel_path}\n")
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    contents.append(f.read())
            except Exception as e:
                contents.append(f"# Error reading file: {str(e)}\n")
    return '\n'.join(contents)

def generate_prompt(root_dir: str, casefold: bool) -> str:
    """
    Combines the folder structure and file contents to create a full project prompt.
    """
    structure = generate_folder_structure(root_dir, casefold)
    contents = append_file_contents(root_dir, casefold)
    return f"Project Structure:\n\n{structure}\n\n{contents}"

def main():
    parser = argparse.ArgumentParser(
        description="Generate project structure and file contents following .gitignore rules"
    )
    parser.add_argument("root_dir", help="Root directory of the project")
    parser.add_argument("output_file", nargs="?", help="Output file (default: stdout)")
    # By default (when --casefold is not provided), matching is case‑sensitive.
    parser.add_argument("--casefold", action="store_true", help="Enable case-insensitive matching (WM_CASEFOLD)")
    global args
    args = parser.parse_args()

    if not os.path.isdir(args.root_dir):
        print(f"Error: {args.root_dir} is not a valid directory")
        return

    prompt = generate_prompt(args.root_dir, casefold=args.casefold)
    if args.output_file:
        with open(args.output_file, 'w', encoding='utf-8') as f:
            f.write(prompt)
        print(f"Output written to {args.output_file}")
    else:
        print(prompt)

if __name__ == "__main__":
    main()
