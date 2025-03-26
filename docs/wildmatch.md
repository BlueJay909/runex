# Wildmatch Matching and Flag Behavior in Runex

This document explains what happens when our wildmatch function is called and how it behaves with respect to different flags, especially **WM_PATHNAME**. We also cover **WM_UNICODE** and **WM_CASEFOLD** briefly. Finally, we discuss how this logic integrates with our core module to strictly enforce Git's .gitignore rules.

---

## Overview of Wildmatch

The `wildmatch` function (a wrapper around the recursive `dowild` function) is responsible for matching wildcard patterns against text (typically filenames or paths). It supports:
  
- `*` : Matches zero or more characters.
- `?` : Matches exactly one character.
- Bracket expressions (e.g., `[abc]`) : Match one character from a set.
- POSIX bracket expressions (e.g., `[[:alpha:]]`) : Are expanded into equivalent "normal regular expression" character classes.

Our implementation also supports three key flags:

- **WM_CASEFOLD**  
  Enables case-insensitive matching.  
  *Example:* With WM_CASEFOLD, `File?.TXT` can match `file1.txt`.

- **WM_UNICODE**  
  Enables Unicode-aware expansions for POSIX bracket expressions.  
  *Example:* With WM_UNICODE, the expression `[[:alpha:]]` will match letters beyond the ASCII range (such as `ñ`), whereas without it, only `[A-Za-z]` would match.

- **WM_PATHNAME**  
  Controls whether wildcards (specifically `*`) are allowed to match the directory separator `/`.

---

## Understanding WM_PATHNAME

### Git’s .gitignore Behavior

In Git, a pattern that does **not** contain a slash is considered a "global" pattern. For example, if your `.gitignore` contains:

```
*.txt
```

Git will ignore **any** file ending in `.txt` regardless of its directory. That means both files in the root and files in any subdirectory will match. For example, consider the following directory structure:

```
.
├── file.txt
└── subdir
    └── file.txt
```

With a `.gitignore` containing `*.txt`, Git ignores both `file.txt` and `subdir/file.txt`.

### How Wildmatch Handles WM_PATHNAME

- **Default Behavior (WM_PATHNAME Off):**  
  When **WM_PATHNAME** is not enabled, the `*` wildcard will match any sequence of characters *including* the directory separator `/`. This is the desired behavior for Git's .gitignore:
  - **Example:**  
    - **Pattern:** `*.txt`  
    - **Matches:**  
      - `file.txt`  
      - `subdir/file.txt`
  
- **When WM_PATHNAME is Enabled:**  
  If you enable **WM_PATHNAME**, then the `*` wildcard will not match the `/` character. This means that wildcards will be restricted to a single directory level.
  - **Example:**  
    - **Pattern:** `*.txt`  
    - **Directory Structure:**
      ```
      .
      ├── file.txt
      └── subdir
          └── file.txt
      ```
    - **Behavior with WM_PATHNAME Enabled:**  
      - The pattern `*.txt` would only match `file.txt` in the root because `*` cannot match the `/` in `subdir/file.txt`.
  
### Why This Matters

Our **core.py** module uses our wildmatch logic to filter files and directories based on .gitignore rules. Git’s default behavior is to treat a pattern like `*.txt` as matching any .txt file anywhere in the directory tree (because Git implicitly treats such patterns as if they were prefixed by `**/`). Therefore, in our integration:
  
- **WM_PATHNAME is left off by default,** so that patterns like `*.txt` match files in subdirectories—exactly as Git does.
  
- If **WM_PATHNAME** were enabled, it would prevent `*` from matching `/`, and patterns like `*.txt` would only match files in the same directory level as the .gitignore file, which would not conform to Git’s rules.

---

## Example Comparison

### Directory Structure

Consider the following project tree:

```
.
├── file.txt
├── image.png
└── docs
    ├── manual.txt
    └── readme.md
```

### .gitignore Content

```
*.txt
```

### Matching Behavior

1. **Default Behavior (WM_PATHNAME Off):**
   - **Pattern:** `*.txt`
   - **Matches:**  
     - `file.txt` (in the root)  
     - `docs/manual.txt` (in a subdirectory)
   - **Outcome:** Both files are ignored, which is the expected Git behavior.

2. **With WM_PATHNAME Enabled:**
   - **Pattern:** `*.txt`
   - **Matches:**  
     - `file.txt` (in the root)  
     - **Does not match:** `docs/manual.txt` because `*` will not match the `/` in `docs/manual.txt`.
   - **Outcome:** Only `file.txt` would be ignored, which deviates from Git's expected behavior.

---

## Integration with core.py

In our **core.py** module, when scanning the project structure against .gitignore rules:
  
- The **GitIgnoreScanner** loads all the patterns from .gitignore files.
- For patterns without a slash (e.g., `*.txt`), our wildmatch function is called **without** the WM_PATHNAME flag enabled (or with WM_PATHNAME off by default). This means the `*` wildcard matches across directory boundaries.
- This ensures that a pattern like `*.txt` matches both `file.txt` and `docs/manual.txt`, exactly as Git would ignore them.
- In summary, our core logic ensures that the default behavior (WM_PATHNAME off, WM_UNICODE as required) strictly follows Git’s .gitignore rules.

---

## Summary

- **Wildmatch** implements wildcard matching using `*`, `?`, and bracket expressions.
- **WM_CASEFOLD** makes matching case-insensitive when enabled.
- **WM_UNICODE** makes POSIX bracket expressions Unicode-aware.
- **WM_PATHNAME**—when enabled—prevents `*` from matching `/`. However, for Git’s .gitignore behavior, we need WM_PATHNAME to be off so that patterns like `*.txt` match files in any directory.
- Our **core.py** module uses wildmatch in a way that ensures our tool behaves exactly like Git, ignoring files according to the rules specified in .gitignore.

This document should help developers understand both the internal workings of this wildmatch implementation in python and its integration with the rest of the system to enforce .gitignore rules.