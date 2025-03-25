# runex/core.py
import os
import json
from typing import Optional, List, Dict, Union
from .ignore_logic import GitIgnoreScanner

###############################################################################
# Text-based output functions
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
# JSON-based output functions
###############################################################################

def build_tree_data(root_dir: str, scanner: GitIgnoreScanner, parent_path: str = "") -> Dict[str, Union[str, list]]:
    """
    Returns a nested dictionary representing the directory structure.
    Directories always have a "children" key; file nodes do not.
    """
    full_path = os.path.join(root_dir, parent_path)
    if parent_path == "":
        name = os.path.basename(os.path.abspath(root_dir))
    else:
        name = os.path.basename(parent_path)
    
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
                        node["children"].append({"name": nm})
        except PermissionError:
            pass
    else:
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
# Public API: generate_prompt
###############################################################################

def generate_prompt(root_dir: str, casefold: bool, json_mode: bool = False, only_structure: bool = False, display_actual_root: bool = True) -> str:
    """
    Generates a full project prompt from a directory, based on .gitignore rules.
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
        base = os.path.basename(os.path.abspath(root_dir)) if display_actual_root else "."
        tree_data = build_tree_data(root_dir, scanner, parent_path="")
        tree_data["name"] = base
        result = {"structure": tree_data}
        if not only_structure:
            files_data = append_file_contents_data(root_dir, scanner)
            result["files"] = files_data
        return json.dumps(result, indent=2)
