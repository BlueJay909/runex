#!/usr/bin/env python
"""
Main Prompt Generator - Generates Folder structure and appends file contents

This script builds a textual representation of a project's folder structure
and appends the contents of files (excluding those ignored by .gitignore rules)
to generate a complete project prompt. Optionally, the output can be produced
in JSON format and/or only the directory structure can be shown.
"""

import os
import argparse
import json
from typing import Optional, List, Dict, Union
from modules.ignore_logic import GitIgnoreScanner

###############################################################################
# Text-based output functions (existing logic)
###############################################################################

def build_tree(root_dir: str, prefix: str = "", scanner: Optional[GitIgnoreScanner] = None, parent_path: str = "") -> List[str]:
    """
    Recursively builds a list of strings representing the folder structure.
    """
    if scanner is None:
        # Use the global args.casefold for compatibility with existing tests.
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
    Generates a string representing the folder structure of the project.
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

###############################################################################
# JSON-based output functions (new)
###############################################################################

def build_tree_data(root_dir: str, scanner: GitIgnoreScanner, parent_path: str = "") -> Dict[str, Union[str, list]]:
    """
    Returns a nested dictionary representing the directory structure.
    Example:
    {
      "name": "myproject",
      "children": [
         {"name": ".gitignore", "children": []},
         {"name": "folderA", "children": [ ... ]}
      ]
    }
    """
    full_path = os.path.join(root_dir, parent_path)
    node = {"name": os.path.basename(full_path) if parent_path else os.path.basename(root_dir), "children": []}
    try:
        for name in sorted([x for x in os.listdir(full_path) if x != '.git']):
            is_dir = os.path.isdir(os.path.join(full_path, name))
            rel_path = os.path.join(parent_path, name) if parent_path else name
            if not scanner.should_ignore(rel_path, is_dir):
                if is_dir:
                    node["children"].append(build_tree_data(root_dir, scanner, rel_path))
                else:
                    node["children"].append({"name": name, "children": []})
    except PermissionError:
        pass
    return node

def append_file_contents_data(root_dir: str, scanner: GitIgnoreScanner) -> List[Dict[str, str]]:
    """
    Returns a list of dictionaries describing each non-ignored file.
    Each dictionary has keys: filename, path, and content.
    """
    files_data = []
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
            entry = {"filename": filename, "path": rel_path}
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    entry["content"] = f.read()
            except Exception as e:
                entry["content"] = f"# Error reading file: {str(e)}"
            files_data.append(entry)
    return files_data

###############################################################################
# The main "generate_prompt" function with optional JSON and only-structure flags.
###############################################################################

def generate_prompt(root_dir: str, casefold: bool, json_mode: bool = False, only_structure: bool = False) -> str:
    """
    Combines the folder structure and file contents to create a full project prompt.
    
    If json_mode is True, outputs a JSON string; if only_structure is True, omits file contents.
    
    Existing behavior (text output with both structure and file contents) is preserved by default.
    """
    if not json_mode:
        structure = generate_folder_structure(root_dir, casefold)
        if only_structure:
            return f"Project Structure:\n\n{structure}\n"
        else:
            contents = append_file_contents(root_dir, casefold)
            return f"Project Structure:\n\n{structure}\n\n{contents}"
    else:
        scanner = GitIgnoreScanner(root_dir, casefold=casefold)
        scanner.load_patterns()
        tree_data = build_tree_data(root_dir, scanner, parent_path="")
        result = {"structure": tree_data}
        if not only_structure:
            files_data = append_file_contents_data(root_dir, scanner)
            result["files"] = files_data
        return json.dumps(result, indent=2)

###############################################################################
# main() remains nearly unchanged, but passes the new optional flags.
###############################################################################

def main():
    parser = argparse.ArgumentParser(
        description="Generate project structure and file contents following .gitignore rules"
    )
    parser.add_argument("root_dir", help="Root directory of the project")
    parser.add_argument("output_file", nargs="?", help="Output file (default: stdout)")
    parser.add_argument("--casefold", action="store_true", help="Enable case-insensitive matching (WM_CASEFOLD)")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of text")
    parser.add_argument("--only-structure", action="store_true", help="Omit file contents in the output")
    args = parser.parse_args()

    if not os.path.isdir(args.root_dir):
        print(f"Error: {args.root_dir} is not a valid directory")
        return

    prompt = generate_prompt(
        root_dir=args.root_dir,
        casefold=args.casefold,
        json_mode=args.json,
        only_structure=args.only_structure
    )
    if args.output_file:
        with open(args.output_file, 'w', encoding='utf-8') as f:
            f.write(prompt)
        print(f"Output written to {args.output_file}")
    else:
        print(prompt)

if __name__ == "__main__":
    main()
