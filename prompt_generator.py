#!/usr/bin/env python
"""
Main Prompt Generator - Generates Folder structure and appends file contents

This script builds a textual representation of a project's folder structure
and appends the contents of files (excluding those ignored by .gitignore rules)
to generate a complete project prompt.
"""

import os  # Provides functions for interacting with the operating system.
import argparse  # Handles command-line argument parsing.
from typing import Optional  # For type hinting optional parameters.
from modules.ignore_logic import GitIgnoreScanner  # Import custom .gitignore scanning logic.

def build_tree(root_dir: str, prefix: str = "", scanner: Optional[GitIgnoreScanner] = None, parent_path: str = "") -> list:
    """
    Recursively builds a list of strings representing the folder structure.

    Args:
        root_dir: The root directory of the project.
        prefix: A string used for formatting (branch connectors).
        scanner: An instance of GitIgnoreScanner; if None, one is created.
        parent_path: The relative path from the root directory for recursion.

    Returns:
        A list of strings, each representing a line in the folder tree.
    """
    # If no scanner is provided, create one for the given root and load ignore patterns.
    if scanner is None:
        scanner = GitIgnoreScanner(root_dir)
        scanner.load_patterns()

    items = []  # Will hold tuples of (item name, is_directory flag).
    # Construct the full path by joining root and parent paths.
    full_path = os.path.join(root_dir, parent_path)
    try:
        # List items in the current directory (skip the .git folder).
        for name in sorted([x for x in os.listdir(full_path) if x != '.git']):
            # Append a tuple with the item's name and a flag indicating if it's a directory.
            items.append((name, os.path.isdir(os.path.join(full_path, name))))
    except PermissionError:
        # If we don't have permission to read the directory, return an empty list.
        return []

    filtered = []  # Filtered items that are not ignored.
    for name, is_dir in items:
        # Build a relative path for each item.
        rel_path = os.path.join(parent_path, name) if parent_path else name
        # Check if the path should be ignored based on .gitignore rules.
        if scanner.should_ignore(rel_path, is_dir):
            continue  # Skip ignored files or directories.
        filtered.append((name, is_dir))

    lines = []  # Lines representing the formatted tree structure.
    for i, (name, is_dir) in enumerate(filtered):
        # Choose the branch connector based on the item's position.
        connector = "└── " if i == len(filtered) - 1 else "├── "
        # Append a '/' after the name if it's a directory.
        line = f"{prefix}{connector}{name}{'/' if is_dir else ''}"
        lines.append(line)
        # If the item is a directory, recursively build its subtree.
        if is_dir:
            # Choose the extension prefix: spaces or a vertical bar based on position.
            ext = "    " if i == len(filtered) - 1 else "│   "
            # Recursively append the subtree lines.
            lines += build_tree(root_dir, prefix + ext, scanner, os.path.join(parent_path, name))
    return lines

def generate_folder_structure(root_dir: str) -> str:
    """
    Generates a string representing the folder structure of the project.

    Args:
        root_dir: The root directory of the project.

    Returns:
        A single string with the folder structure, with each line separated by a newline.
    """
    # Get the base directory name.
    base = os.path.basename(root_dir)
    # Initialize the scanner and load patterns.
    scanner = GitIgnoreScanner(root_dir)
    scanner.load_patterns()
    # Start with the base folder line.
    lines = [f"{base}/"]
    # Append the recursively built tree structure.
    lines += build_tree(root_dir, scanner=scanner)
    return '\n'.join(lines)

def append_file_contents(root_dir: str) -> str:
    """
    Appends the contents of all non-ignored files (except .gitignore) in the project.

    Args:
        root_dir: The root directory of the project.

    Returns:
        A string that contains headers for each file and their respective content.
    """
    scanner = GitIgnoreScanner(root_dir)
    scanner.load_patterns()
    contents = []  # This will hold the complete file contents.
    # Walk through the directory tree.
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Exclude the .git directory from processing.
        if '.git' in dirnames:
            dirnames.remove('.git')
        # Get the directory's relative path.
        rel_dir = os.path.relpath(dirpath, root_dir)
        if rel_dir == '.':
            rel_dir = ''
        # Filter out directories that should be ignored.
        dirnames[:] = [d for d in dirnames if not scanner.should_ignore(os.path.join(rel_dir, d), True)]
        # Process each file in the current directory.
        for filename in sorted(filenames):
            # Skip the .gitignore file itself.
            if filename == ".gitignore":
                continue
            # Build the file's relative path.
            rel_path = os.path.join(rel_dir, filename) if rel_dir else filename
            # Skip the file if it should be ignored.
            if scanner.should_ignore(rel_path, False):
                continue
            full_path = os.path.join(dirpath, filename)
            # Add file header information.
            contents.append(f"\n# File: {filename}")
            contents.append(f"# Path: {rel_path}\n")
            try:
                # Open and read the file contents.
                with open(full_path, 'r', encoding='utf-8') as f:
                    contents.append(f.read())
            except Exception as e:
                # In case of an error (e.g., binary file, permission issue), log the error message.
                contents.append(f"# Error reading file: {str(e)}\n")
    return '\n'.join(contents)

def generate_prompt(root_dir: str) -> str:
    """
    Combines the folder structure and file contents to create a full project prompt.

    Args:
        root_dir: The root directory of the project.

    Returns:
        A string combining the project structure and file contents.
    """
    structure = generate_folder_structure(root_dir)
    contents = append_file_contents(root_dir)
    # Format the final prompt by combining both parts.
    return f"Project Structure:\n\n{structure}\n\n{contents}"

def main():
    """
    Main function to parse command-line arguments, generate the prompt,
    and either print it to stdout or write it to an output file.
    """
    parser = argparse.ArgumentParser(
        description="Generate project structure and file contents following .gitignore rules"
    )
    # Define the root directory argument.
    parser.add_argument("root_dir", help="Root directory of the project")
    # Optionally, define an output file argument (if not provided, defaults to stdout).
    parser.add_argument("output_file", nargs="?", help="Output file (default: stdout)")
    args = parser.parse_args()

    # Validate that the provided root_dir is indeed a directory.
    if not os.path.isdir(args.root_dir):
        print(f"Error: {args.root_dir} is not a valid directory")
        return

    # Generate the complete project prompt.
    prompt = generate_prompt(args.root_dir)
    if args.output_file:
        # If an output file is specified, write the prompt to that file.
        with open(args.output_file, 'w', encoding='utf-8') as f:
            f.write(prompt)
        print(f"Output written to {args.output_file}")
    else:
        # Otherwise, print the prompt to stdout.
        print(prompt)

# Standard boilerplate to execute main() when the script is run directly.
if __name__ == "__main__":
    main()
