---
layout: default
title: Core Module
---

# Core Module for Runex – Technical Overview

This document explains how the core module (core.py) works. It focuses on what each function does and clearly explains the difference between "only structure" mode (the `-s` flag) and the default mode that includes file contents.

---

## 1. Text-Based Output Functions

These functions generate a plain text view of the project directory.

### build_tree

- **What It Does:**  
  Recursively builds a list of strings that represent the directory tree.
  
- **How It Works:**  
  - It uses a `GitIgnoreScanner` to load .gitignore patterns.
  - It lists all items in a directory (ignoring `.git`), marks each item as file or directory.
  - It filters out items that should be ignored.
  - For each remaining item, it builds a visual line using connectors ("├── " or "└── ").
  - If an item is a directory, it calls itself recursively and adds an indented tree for that subdirectory.

- **Example Output:**  
  For a project structured like this:
  
  ```
  my_project/
  ├── file.txt
  └── docs/
      ├── manual.txt
      └── readme.md
  ```
  
  `build_tree` returns:
  
  ```
  my_project/
  ├── file.txt
  └── docs/
      ├── manual.txt
      └── readme.md
  ```

### generate_folder_structure

- **What It Does:**  
  Returns the entire folder structure as one text string.
  
- **How It Works:**  
  - Determines the root name (either the actual folder name or `.` based on the `display_actual_root` flag).
  - Initializes a `GitIgnoreScanner` with optional case-insensitive matching.
  - Calls `build_tree` starting from the root.
  - Joins all the tree lines into a single string.

### append_file_contents

- **What It Does:**  
  Appends the contents of every non-ignored file (except .gitignore files) to the text output.
  
- **How It Works:**  
  - Walks the entire directory tree.
  - For each file not ignored by .gitignore, it adds a header (with file name and relative path) and then the file's content.
  - If reading a file fails, it adds an error message instead.

---

## 2. JSON-Based Output Functions

These functions produce a JSON representation of the project structure.

### build_tree_data

- **What It Does:**  
  Builds a nested dictionary to represent the directory tree.
  
- **How It Works:**  
  - Directories become dictionaries with `"name"` and a `"children"` list.
  - Files are represented as dictionaries with just a `"name"`.
  - It recursively builds this structure, filtering out ignored items.

### append_file_contents_data

- **What It Does:**  
  Returns a list of dictionaries, each describing a non-ignored file.
  
- **How It Works:**  
  - Walks through the project.
  - For each file (that is not ignored), it collects:
    - `"filename"`: The file's name.
    - `"path"`: The file's relative path.
    - `"content"`: The content of the file (or an error message if it fails to read).

---

## 3. Public API: generate_prompt

- **What It Does:**  
  Combines the above functions to generate the final project prompt.
  
- **Modes:**
  - **Plain Text Mode (Default):**  
    - Calls `generate_folder_structure` to produce a visual tree.
    - If the `only_structure` flag is **not** set, it also calls `append_file_contents` to add file contents below the tree.
  - **JSON Mode:**  
    - Uses `build_tree_data` to create a nested dictionary of the structure.
    - Optionally adds file details via `append_file_contents_data`.
    - Converts the final dictionary to a JSON-formatted string.
  
- **Key Parameter – only_structure (`-s` Flag):**  
  - **Only Structure Mode (-s):**  
    - **Output:** The project prompt will show only the folder tree, with no file contents.
    - **Use Case:** Useful when you want a quick overview of the project structure.
  - **Default Mode (without -s):**  
    - **Output:** The project prompt includes both the folder structure and, appended below, the contents of every non-ignored file.
    - **Use Case:** Use this when you need full context including file contents.

---

## Integration with Git's .gitignore Rules

- **How It Works:**  
  - The module uses the `GitIgnoreScanner` (from ignore_logic.py) to load .gitignore patterns.
  - Every time a file or directory is processed, the scanner is used to check if it should be ignored.
  - This ensures that the final output (in both text and JSON modes) strictly follows the same rules as Git: files ignored by .gitignore are omitted from the output.
  
- **Example Scenario:**  
  Suppose your project has:
  
  ```
  my_project/
  ├── file.txt
  ├── temp.log
  └── docs/
      └── manual.txt
  ```
  
  And your `.gitignore` contains:
  
  ```
  *.log
  ```
  
  The scanner will ignore `temp.log`.  
  - In **only structure mode (-s):**  
    The output tree will show `my_project/`, `file.txt`, and `docs/` (with `manual.txt` inside), but `temp.log` will be missing.
  - In **default mode:**  
    The tree and the appended file contents will also exclude `temp.log`.

---

## Conclusion

- The **core.py** module converts a project directory into either a plain text tree (with optional file contents) or a JSON object.
- The **only_structure** flag (-s) controls whether file contents are included.
- The module relies on a `GitIgnoreScanner` to enforce .gitignore rules, ensuring that ignored files are not part of the output.
- This design allows for both quick visual overviews and detailed context of the project, while always following Git's ignore behavior.
