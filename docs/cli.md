---
layout: default
title: CLI module
nav: true
---

# CLI Module (runex/cli.py) – Usage Examples

This document explains how to use the CLI tool and what to expect for each option. The CLI is built with Click and calls `generate_prompt()` from `runex.core`. Below are some practical usage scenarios with examples of the initial directory structure, sample .gitignore content (if applicable), and the expected output.

---

## 1. Default Mode (No Options)

**Command:**

```bash
runex my_project
```

**Initial Directory Structure:**

```
my_project/
├── .gitignore       # (Empty or irrelevant)
├── file.txt         # Contains some text
└── docs/
    └── manual.txt   # Contains manual content
```

**.gitignore Content:**  
Assume it's empty or does not ignore any files.

**Expected Output (Plain Text):**

- A visual tree showing all folders and files.
- The output includes the contents of `file.txt` and `docs/manual.txt` appended after the tree.

Example snippet:

```
my_project/
├── file.txt
└── docs/
    └── manual.txt

# File: file.txt
# Path: file.txt
(Contents of file.txt)

# File: manual.txt
# Path: docs/manual.txt
(Contents of manual.txt)
```

---

## 2. Only Structure Mode (-s)

**Command:**

```bash
runex my_project -s
```

**Initial Directory Structure:**

(Same as above.)

**.gitignore Content:**  
Not relevant for this example.

**Expected Output (Plain Text):**

- A visual tree showing only the folder structure.
- **No file contents** are appended.

Example snippet:

```
my_project/
├── file.txt
└── docs/
    └── manual.txt
```

---

## 3. JSON Mode (-oj)

**Command:**

```bash
runex my_project -oj
```

**Initial Directory Structure:**

(Same as above.)

**.gitignore Content:**  
Not relevant.

**Expected Output (JSON):**

A JSON object with two main keys:
- **"structure"**: A nested dictionary representing the directory tree.
- **"files"**: A list of dictionaries, each containing:
  - `"filename"`: Name of the file.
  - `"path"`: Relative path of the file.
  - `"content"`: The file's content.

Example snippet:

```json
{
  "structure": {
    "name": "my_project",
    "children": [
      { "name": ".gitignore" },
      { "name": "file.txt" },
      {
        "name": "docs",
        "children": [
          { "name": "manual.txt" }
        ]
      }
    ]
  },
  "files": [
    {
      "filename": "file.txt",
      "path": "file.txt",
      "content": "(Contents of file.txt)"
    },
    {
      "filename": "manual.txt",
      "path": "docs/manual.txt",
      "content": "(Contents of manual.txt)"
    }
  ]
}
```

---

## 4. Case-Insensitive Matching (-c)

**Command:**

```bash
runex my_project -c
```

**Scenario:**

- Suppose `.gitignore` contains `*.txt`, and there’s a file named `FILE.TXT`.
- With **WM_CASEFOLD** enabled (via the `-c` flag), the matching is case-insensitive.
- Thus, `FILE.TXT` will be ignored if the pattern specifies that.

**Expected Output:**

- The output will follow the default mode (plain text with file contents), but files like `FILE.TXT` will be considered ignored if they match the .gitignore pattern in a case-insensitive way.

---

## 5. Relative Root Mode (-rr)

**Command:**

```bash
runex my_project -rr
```

**Scenario:**

- Instead of displaying the actual directory name as the root (e.g., `my_project/`), the tool will display a dot (`./`).
  
**Expected Output:**

- The tree will start with `./` instead of `my_project/`.
  
Example snippet:

```
./
├── file.txt
└── docs/
    └── manual.txt
```

---

## 6. Combining Options

**Command:**

```bash
runex my_project -s -oj -c -rr
```

**Scenario:**

- **-s:** Only display the folder structure.
- **-oj:** Output in JSON format.
- **-c:** Enable case-insensitive matching.
- **-rr:** Display the root as `.` instead of the actual folder name.

**Initial Directory Structure:**

(Same as before.)

**Expected Output (JSON Only Structure):**

A JSON object with a `"structure"` key only (no `"files"` key). The root will be shown as `"."`.

Example snippet:

```json
{
  "structure": {
    "name": ".",
    "children": [
      { "name": ".gitignore" },
      { "name": "file.txt" },
      {
        "name": "docs",
        "children": [
          { "name": "manual.txt" }
        ]
      }
    ]
  }
}
```

---

## Summary

- **Default Mode:**  
  Generates a text tree with appended file contents.
  
- **-s (Only Structure):**  
  Outputs only the directory tree, omitting file contents.
  
- **-oj (JSON Mode):**  
  Produces JSON output, with keys for structure and files.
  
- **-c (Case-Insensitive):**  
  Matches patterns without regard to letter case.
  
- **-rr (Relative Root):**  
  Uses `.` as the root node instead of the actual directory name.

The CLI uses these options to call `generate_prompt()` from `runex.core`, ensuring that the project prompt strictly follows Git's .gitignore rules. This flexible design lets developers choose the format and level of detail they need.

---