"""
Core Module for Runex

This module implements the main functionality for generating a project prompt.
It scans a project's directory structure, applies .gitignore rules to filter out
unwanted files/directories, and produces either a plain text tree view (with optional
file contents appended) or a JSON representation of the project structure.

The module is divided into three main sections:

1. Text-based Output Functions:
   - build_tree: Recursively builds a visual tree (list of strings) of the directory structure.
   - generate_folder_structure: Generates the complete folder structure as a text string.
   - append_file_contents: Appends file contents (with headers) to the text output.

2. JSON-based Output Functions:
   - build_tree_data: Constructs a nested dictionary representing the directory tree.
   - append_file_contents_data: Gathers file details (name, path, content) into a list of dictionaries.

3. Public API:
   - generate_prompt: Combines the above functions to generate the final project prompt,
     either in plain text or JSON format, with options to include only the structure or both
     structure and file contents.
"""

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

    Parameters:
        root_dir (str): The base directory of the project.
        prefix (str): The current indentation/prefix string used to visually represent the tree.
        scanner (Optional[GitIgnoreScanner]): An instance for applying .gitignore rules. If None, a new scanner is created.
        parent_path (str): The relative path from the root_dir to the current directory being processed.

    Returns:
        List[str]: A list of strings, each representing a line in the visual directory tree.
    """
    # If no scanner is provided, create one and load its ignore patterns.
    if scanner is None:
        scanner = GitIgnoreScanner(root_dir)
        scanner.load_patterns()

    # List to store (name, is_directory) tuples for each item in the current directory.
    items = []
    # Compute the full path for the current directory level.
    full_path = os.path.join(root_dir, parent_path)
    try:
        # List and sort all entries in the current directory, excluding the '.git' directory.
        for name in sorted([x for x in os.listdir(full_path) if x != '.git']):
            items.append((name, os.path.isdir(os.path.join(full_path, name))))
    except PermissionError:
        # If permission is denied, return an empty list to skip processing this directory.
        return []

    # Filter items that are not ignored according to .gitignore rules.
    filtered = []
    for name, is_dir in items:
        # Compute the relative path for the current item.
        rel_path = os.path.join(parent_path, name) if parent_path else name
        # Skip the item if it should be ignored.
        if scanner.should_ignore(rel_path, is_dir):
            continue
        filtered.append((name, is_dir))

    # Build the visual tree lines.
    lines = []
    for i, (name, is_dir) in enumerate(filtered):
        # Determine the connector: use "└── " for the last item, otherwise "├── ".
        connector = "└── " if i == len(filtered) - 1 else "├── "
        # Construct the line with the current prefix and a '/' if the item is a directory.
        line = f"{prefix}{connector}{name}{'/' if is_dir else ''}"
        lines.append(line)
        # If the item is a directory, recursively process its contents.
        if is_dir:
            # Determine the prefix extension based on whether the item is the last in its level.
            ext = "    " if i == len(filtered) - 1 else "│   "
            # Recursively build the tree for the subdirectory and append the results.
            lines += build_tree(root_dir, prefix + ext, scanner, os.path.join(parent_path, name))
    return lines

def generate_folder_structure(root_dir: str, casefold: bool, display_actual_root: bool = True) -> str:
    """
    Generates a string representing the entire folder structure of the project.

    This function initializes the GitIgnoreScanner, constructs the visual tree starting
    from the root, and returns the result as a single string.

    Parameters:
        root_dir (str): The project's root directory.
        casefold (bool): If True, matching for ignore rules is case-insensitive.
        display_actual_root (bool): If True, displays the actual folder name as the root node; if False, uses '.'.

    Returns:
        str: The complete folder structure as a text string.
    """
    # Determine the root name to display.
    if display_actual_root:
        base = os.path.basename(os.path.abspath(root_dir))
    else:
        base = "."
    # Initialize the scanner with the specified case sensitivity.
    scanner = GitIgnoreScanner(root_dir, casefold=casefold)
    scanner.load_patterns()
    # Begin the tree with the root node.
    lines = [f"{base}/"]
    # Append the recursively built tree.
    lines += build_tree(root_dir, scanner=scanner)
    return '\n'.join(lines)

def append_file_contents(root_dir: str, casefold: bool) -> str:
    """
    Appends the contents of all non-ignored files (excluding .gitignore files) in the project.

    This function traverses the entire directory tree, and for each file that is not ignored,
    it appends a header (showing the file's name and relative path) followed by its content.
    If a file cannot be read, an error message is appended instead.

    Parameters:
        root_dir (str): The project's root directory.
        casefold (bool): If True, matching for ignore rules is case-insensitive.

    Returns:
        str: A single string containing the headers and contents of non-ignored files.
    """
    # Create and configure a GitIgnoreScanner.
    scanner = GitIgnoreScanner(root_dir, casefold=casefold)
    scanner.load_patterns()
    contents = []
    # Walk through the directory tree.
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Exclude the '.git' directory from processing.
        if '.git' in dirnames:
            dirnames.remove('.git')
        # Compute the relative directory path from the root.
        rel_dir = os.path.relpath(dirpath, root_dir)
        if rel_dir == '.':
            rel_dir = ''
        # Remove directories that should be ignored.
        dirnames[:] = [d for d in dirnames if not scanner.should_ignore(os.path.join(rel_dir, d), True)]
        # Process each file in the directory.
        for filename in sorted(filenames):
            # Skip .gitignore files.
            if filename == ".gitignore":
                continue
            # Build the relative path for the file.
            rel_path = os.path.join(rel_dir, filename) if rel_dir else filename
            # Skip files that match ignore rules.
            if scanner.should_ignore(rel_path, False):
                continue
            full_path = os.path.join(dirpath, filename)
            # Append a header for the file.
            contents.append(f"\n# File: {filename}")
            contents.append(f"# Path: {rel_path}\n")
            try:
                # Read and append the file's content.
                with open(full_path, 'r', encoding='utf-8') as f:
                    contents.append(f.read())
            except Exception as e:
                # On error, append an error message.
                contents.append(f"# Error reading file: {str(e)}\n")
    return '\n'.join(contents)

###############################################################################
# JSON-based output functions
###############################################################################

def build_tree_data(root_dir: str, scanner: GitIgnoreScanner, parent_path: str = "") -> Dict[str, Union[str, list]]:
    """
    Constructs a nested dictionary representing the directory structure.

    Directories are represented as dictionaries with a "name" key and a "children" key
    (which holds a list of sub-items). Files are represented as dictionaries with just a "name" key.

    Parameters:
        root_dir (str): The project's root directory.
        scanner (GitIgnoreScanner): The scanner with loaded .gitignore rules.
        parent_path (str): The relative path from the root_dir to the current directory.

    Returns:
        Dict[str, Union[str, list]]: A dictionary representing the directory tree.
    """
    # Compute the full path for the current node.
    full_path = os.path.join(root_dir, parent_path)
    # Determine the name for the current node.
    if parent_path == "":
        name = os.path.basename(os.path.abspath(root_dir))
    else:
        name = os.path.basename(parent_path)
    
    # Check if the current path is a directory.
    if os.path.isdir(full_path):
        # Create a node with a "name" and an empty "children" list.
        node = {"name": name, "children": []}
        try:
            # Iterate over items in the directory, skipping '.git'.
            for nm in sorted([x for x in os.listdir(full_path) if x != '.git']):
                is_dir = os.path.isdir(os.path.join(full_path, nm))
                # Compute the relative path for this item.
                rel_path = os.path.join(parent_path, nm) if parent_path else nm
                # Only include items that are not ignored.
                if not scanner.should_ignore(rel_path, is_dir):
                    if is_dir:
                        # Recursively build data for subdirectories.
                        node["children"].append(build_tree_data(root_dir, scanner, rel_path))
                    else:
                        # For files, create a simple node with just the name.
                        node["children"].append({"name": nm})
        except PermissionError:
            # Skip directory if access is denied.
            pass
    else:
        # For non-directory nodes, return a simple node.
        node = {"name": name}
    return node

def append_file_contents_data(root_dir: str, scanner: GitIgnoreScanner) -> List[Dict[str, str]]:
    """
    Collects details for each non-ignored file as a list of dictionaries.

    Each dictionary includes:
        - 'filename': The name of the file.
        - 'path': The file's relative path from the root.
        - 'content': The file's content, or an error message if the file couldn't be read.

    Parameters:
        root_dir (str): The project's root directory.
        scanner (GitIgnoreScanner): The scanner with loaded .gitignore rules.

    Returns:
        List[Dict[str, str]]: A list of dictionaries describing each file.
    """
    files_data = []
    # Walk the directory tree.
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Exclude the '.git' directory.
        if '.git' in dirnames:
            dirnames.remove('.git')
        # Compute the relative directory path.
        rel_dir = os.path.relpath(dirpath, root_dir)
        if rel_dir == '.':
            rel_dir = ''
        # Remove ignored directories from further processing.
        dirnames[:] = [d for d in dirnames if not scanner.should_ignore(os.path.join(rel_dir, d), True)]
        # Process each file.
        for filename in sorted(filenames):
            if filename == ".gitignore":
                continue
            # Construct the file's relative path.
            rel_path = os.path.join(rel_dir, filename) if rel_dir else filename
            # Skip files that should be ignored.
            if scanner.should_ignore(rel_path, False):
                continue
            full_path = os.path.join(dirpath, filename)
            entry = {"filename": filename, "path": rel_path}
            try:
                # Read the file's content.
                with open(full_path, 'r', encoding='utf-8') as f:
                    entry["content"] = f.read()
            except Exception as e:
                # On error, record an error message.
                entry["content"] = f"# Error reading file: {str(e)}"
            files_data.append(entry)
    return files_data

###############################################################################
# Public API: generate_prompt
###############################################################################

def generate_prompt(root_dir: str, casefold: bool, json_mode: bool = False, only_structure: bool = False, display_actual_root: bool = True) -> str:
    """
    Generates the final project prompt based on .gitignore rules.

    Depending on the provided options, this function can produce:
      - Plain text output: A visual directory tree (with optional file contents appended).
      - JSON output: A structured representation of the directory tree, optionally including file details.

    Parameters:
        root_dir (str): The root directory to scan.
        casefold (bool): If True, ignore rules are matched case-insensitively.
        json_mode (bool): If True, output is formatted as JSON; otherwise, plain text is returned.
        only_structure (bool): If True, only the folder structure is included (file contents omitted).
        display_actual_root (bool): If True, the root node displays the actual folder name; if False, it displays '.'.

    Returns:
        str: The complete project prompt as a plain text string or JSON-formatted string.
    """
    if not json_mode:
        # Generate a plain text folder structure.
        structure = generate_folder_structure(root_dir, casefold, display_actual_root)
        if only_structure:
            # If only structure is required, return it.
            return f"Project Structure:\n\n{structure}\n"
        else:
            # Otherwise, append file contents to the structure.
            contents = append_file_contents(root_dir, casefold)
            return f"Project Structure:\n\n{structure}\n\n{contents}"
    else:
        # For JSON output, initialize a scanner and load ignore patterns.
        scanner = GitIgnoreScanner(root_dir, casefold=casefold)
        scanner.load_patterns()
        # Determine the root node name.
        base = os.path.basename(os.path.abspath(root_dir)) if display_actual_root else "."
        # Build the directory tree as a nested dictionary.
        tree_data = build_tree_data(root_dir, scanner, parent_path="")
        tree_data["name"] = base  # Ensure the root node has the correct name.
        result = {"structure": tree_data}
        if not only_structure:
            # Add file details if file contents are required.
            files_data = append_file_contents_data(root_dir, scanner)
            result["files"] = files_data
        # Convert the final result to a JSON string.
        return json.dumps(result, indent=2)
