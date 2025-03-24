#!/usr/bin/env python
"""
Main Prompt Generator - Generates Folder structure and appends file contents

This script builds a textual or JSON representation of a project's folder structure
and (optionally) appends the contents of files (excluding those ignored by .gitignore rules)
to generate a complete project prompt.
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
    Recursively builds a list of strings representing the folder structure in text form.
    """
    if scanner is None:
        scanner = GitIgnoreScanner(root_dir)
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

def generate_folder_structure(root_dir: str, casefold: bool, display_actual_root: bool = True) -> str:
    """
    Generates a string representing the folder structure of the project.
    If display_actual_root is True (default), the actual folder name (from the absolute path)
    is used as the root node; otherwise, "." is used.
    """
    if display_actual_root:
        base = os.path.basename(os.path.abspath(root_dir))
    else:
        base = "."
    scanner = GitIgnoreScanner(root_dir, casefold=casefold)
    scanner.load_patterns()
    lines = [f"{base}/"]
    lines += build_tree(root_dir, scanner=scanner)
    return '\n'.join(lines)

def append_file_contents(root_dir: str, casefold: bool) -> str:
    """
    Appends the contents of all non-ignored files (except .gitignore) in the project (text form).
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
    
    - For directories, the returned node always has a "children" key (which may be empty).
    - For files, the node is represented simply as {"name": <filename>}.
    """
    full_path = os.path.join(root_dir, parent_path)
    if parent_path == "":
        # For the root node, use the absolute folder name.
        name = os.path.basename(os.path.abspath(root_dir))
    else:
        name = os.path.basename(parent_path)
    
    # Check if this is a directory
    if os.path.isdir(full_path):
        node = {"name": name, "children": []}
        try:
            for nm in sorted([x for x in os.listdir(full_path) if x != '.git']):
                is_dir = os.path.isdir(os.path.join(full_path, nm))
                rel_path = os.path.join(parent_path, nm) if parent_path else nm
                if not scanner.should_ignore(rel_path, is_dir):
                    if is_dir:
                        node["children"].append(build_tree_data(root_dir, scanner, rel_path))
                    else:
                        # For file nodes, do not add a "children" key.
                        node["children"].append({"name": nm})
        except PermissionError:
            pass
    else:
        # If for some reason full_path isn't a directory, return a file node.
        node = {"name": name}
    return node


def append_file_contents_data(root_dir: str, scanner: GitIgnoreScanner) -> List[Dict[str, str]]:
    """
    Returns a list of dictionaries describing each non-ignored file.
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

def generate_prompt(root_dir: str, casefold: bool, json_mode: bool = False, only_structure: bool = False, display_actual_root: bool = True) -> str:
    """
    Combines the folder structure and file contents to create a full project prompt.
    
    - If json_mode is True, output is in JSON format.
    - If only_structure is True, file contents are omitted.
    - If display_actual_root is True (default), the root node shows the actual folder name; if False, it shows ".".
    - In the JSON output, directories always have a "children" key, whereas file nodes do not.
    """
    if not json_mode:
        structure = generate_folder_structure(root_dir, casefold, display_actual_root)
        if only_structure:
            return f"Project Structure:\n\n{structure}\n"
        else:
            contents = append_file_contents(root_dir, casefold)
            return f"Project Structure:\n\n{structure}\n\n{contents}"
    else:
        scanner = GitIgnoreScanner(root_dir, casefold=casefold)
        scanner.load_patterns()
        # Determine the root name.
        base = os.path.basename(os.path.abspath(root_dir)) if display_actual_root else "."
        # Build tree data and override the root name.
        tree_data = build_tree_data(root_dir, scanner, parent_path="")
        tree_data["name"] = base
        result = {"structure": tree_data}
        if not only_structure:
            files_data = append_file_contents_data(root_dir, scanner)
            result["files"] = files_data
        return json.dumps(result, indent=2)

###############################################################################
# main() now supports a new flag: --relative-root which forces the root name to be "."
###############################################################################

def main():
    parser = argparse.ArgumentParser(
        description="Generates a representation of a project directory and file structure following git's .gitignore rules. The output by default appends all file contents. The output can be limited to only display the directory tree omitting the file contents. output formats supported: json, txt ,stdout",
        epilog="Hopefully it was useful!"
    )
    parser.add_argument("root_dir", help="Root directory of the project to be scanned")
    parser.add_argument("output_file", nargs="?", help="Optional output file (default: stdout)")
    parser.add_argument("--casefold", "-c", action="store_true", help="Enable case-insensitive matching (WM_CASEFOLD)")
    parser.add_argument("--json", "-oj", action="store_true", help="Output JSON instead of text")
    parser.add_argument("--only-structure", "-s", action="store_true", help="Omit file contents in the output")
    parser.add_argument("--relative-root", "-rr", action="store_true", help="Force the root directory name to be '.' insted of basename")
    args = parser.parse_args()

    root_dir = args.root_dir
    if not os.path.isdir(root_dir):
        print(f"Error: {root_dir} is not a valid directory")
        return

    # Determine the root display mode:
    # If --relative-root is provided, display_actual_root is False.
    display_actual_root = not args.relative_root

    prompt = generate_prompt(
        root_dir=root_dir,
        casefold=args.casefold,
        json_mode=args.json,
        only_structure=args.only_structure,
        display_actual_root=display_actual_root
    )
    if args.output_file:
        with open(args.output_file, 'w', encoding='utf-8') as f:
            f.write(prompt)
        print(f"Output written to {args.output_file}")
    else:
        print(prompt)

if __name__ == "__main__":
    main()
