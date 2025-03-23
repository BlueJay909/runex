#!/usr/bin/env python
import os
import re
import shutil
import tempfile
import unittest
from prompt_generator import generate_prompt
from modules.ignore_logic import GitIgnoreScanner

class ExtremeTest(unittest.TestCase):
    def setUp(self):
        # Create a temporary repository directory for each test.
        self.repo_dir = tempfile.mkdtemp(prefix="extreme_test_")
    
    def tearDown(self):
        # Remove the temporary directory after each test.
        shutil.rmtree(self.repo_dir)
    
    def create_file(self, rel_path, content=""):
        path = os.path.join(self.repo_dir, rel_path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
    
    def create_structure(self, structure, base_path=""):
        """
        Recursively create files and directories.
        'structure' is a dict where keys are names and values are either strings (file content)
        or dicts (subdirectories).
        """
        for name, content in structure.items():
            path = os.path.join(self.repo_dir, base_path, name)
            if isinstance(content, dict):
                os.makedirs(path, exist_ok=True)
                self.create_structure(content, os.path.join(base_path, name))
            else:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
    
    def get_tree_section(self, output):
        """
        Extract the folder-tree section from the generated prompt.
        Assumes the prompt is structured as:
          Project Structure:
          
          <tree>
          
          <file contents>
        """
        parts = output.split("\n\n")
        return parts[1] if len(parts) >= 2 else ""
    
    def debug_print_output(self, output):
        print("DEBUG: Full Prompt Output:")
        print(output)
        print("DEBUG: Extracted Directory Tree:")
        print(self.get_tree_section(output))
    
    def test_extremely_deep_nested(self):
        """
        Create a 10-level deep structure.
          - Each level has a file "junk.tmp" (should be ignored).
          - Levels 5 and deeper also have "keep.tmp" (should be unignored).
        Root .gitignore ignores all "*.tmp" files.
        A nested .gitignore in level5 unignores "keep.tmp" files.
        
        Expected behavior:
          - No "junk.tmp" files appear anywhere.
          - "keep.tmp" appears only in level5 (and deeper).
        """
        deep = {}
        current = deep
        for i in range(1, 11):
            folder = f"level{i}"
            current[folder] = {}
            current[folder]["junk.tmp"] = f"junk at level {i}"
            if i >= 5:
                current[folder]["keep.tmp"] = f"keep at level {i}"
            current = current[folder]
        
        self.create_structure(deep)
        self.create_file(".gitignore", "*.tmp\n")
        self.create_file("level1/level2/level3/level4/level5/.gitignore", "!keep.tmp\n")
        
        output = generate_prompt(self.repo_dir, casefold=False)
        self.debug_print_output(output)
        tree = self.get_tree_section(output)
        # Assert that no line at the root of the tree shows a file named "junk.tmp"
        self.assertNotRegex(tree, r"^[├└]\s+junk\.tmp$", "No root-level junk.tmp should appear")
        # Assert that a line for "keep.tmp" appears under a nested directory (level5 or deeper)
        self.assertRegex(output, r"# Path:\s+level1/level2/level3/level4/level5(?:/|\\).*keep\.tmp", 
                         "keep.tmp in level5 should be unignored")
    
    def test_complex_wildcards_and_posix(self):
        """
        Root .gitignore:
            - Ignores files matching "temp*[0-9].txt"
            - Unignores files matching "temp[[:digit:]]_keep.txt"
        
        Files created:
            - "temp123.txt" and "temp9.txt" should be ignored.
            - "temp5_keep.txt" should be unignored.
            - "tempx.txt" should be kept.
        
        Expected behavior:
            - The file contents section should not include headers with "# Path: temp123.txt" or "temp9.txt".
            - The header for "temp5_keep.txt" should appear.
            - "tempx.txt" should appear as a kept file.
        """
        self.create_file(".gitignore", "temp*[0-9].txt\n!temp[[:digit:]]_keep.txt\n")
        self.create_file("temp123.txt", "ignored")
        self.create_file("temp9.txt", "ignored")
        self.create_file("temp5_keep.txt", "kept")
        self.create_file("tempx.txt", "not ignored")
        
        output = generate_prompt(self.repo_dir, casefold=False)
        self.debug_print_output(output)
        # Check file contents section for expected paths.
        self.assertNotIn("# Path: temp123.txt", output, "temp123.txt should be ignored")
        self.assertNotIn("# Path: temp9.txt", output, "temp9.txt should be ignored")
        self.assertIn("# Path: temp5_keep.txt", output, "temp5_keep.txt should be unignored")
        self.assertIn("# Path: tempx.txt", output, "tempx.txt should be kept")
    
    def test_negations_conflicting_rules(self):
        """
        Root .gitignore:
            - Ignores all ".log" files.
            - Unignores files matching "debug/*.log".
        
        Files:
            - "app.log" at root should be ignored.
            - "debug/app.log" should be unignored.
        
        Expected behavior:
            - The directory tree should not show a root-level "app.log" line.
            - The file contents section should contain "# Path: debug/app.log".
        """
        self.create_file(".gitignore", "*.log\n!debug/*.log\n")
        self.create_file("app.log", "ignored")
        self.create_file("debug/app.log", "kept")
        
        output = generate_prompt(self.repo_dir, casefold=False)
        self.debug_print_output(output)
        tree = self.get_tree_section(output)
        self.assertNotRegex(tree, r"^[├└]\s+app\.log$", "Root-level app.log should be ignored")
        self.assertIn("# Path: debug/app.log", output, "debug/app.log should be unignored")
    
    def test_deep_structure_without_nested_gitignore_with_negation(self):
        """
        Root .gitignore:
            - Ignores all ".tmp" files.
            - Unignores files matching "include/*.tmp".
        
        Files:
            - "app.tmp" at the root should be ignored.
            - "include/app.tmp" should be unignored.
        
        Expected behavior:
            - The directory tree should not contain a line for a root-level "app.tmp".
            - The file contents section should include "# Path: include/app.tmp".
        """
        self.create_file(".gitignore", "*.tmp\n!include/*.tmp\n")
        self.create_file("app.tmp", "ignored")
        self.create_file("include/app.tmp", "kept")
        
        output = generate_prompt(self.repo_dir, casefold=False)
        self.debug_print_output(output)
        tree = self.get_tree_section(output)
        self.assertNotRegex(tree, r"^[├└]\s+app\.tmp$", "Root-level app.tmp should be ignored")
        self.assertIn("# Path: include/app.tmp", output, "include/app.tmp should be unignored")

    # Fails because [[:alpha:]] still falls back to ASCII
    def test_unicode_and_special_characters(self):
        """
        Create a structure with Unicode file and folder names and special characters.
        Root .gitignore ignores files that start with a Unicode letter using a POSIX bracket.
        
        Files:
            - "résumé.txt" and "文档.txt" (starting with letters) should be ignored.
            - "123.txt" (starting with a digit) should be kept.
        
        Expected behavior:
            - The file contents section should not contain "# Path:" lines for "résumé.txt" or "文档.txt".
            - It should contain "# Path: 123.txt".
        """
        self.create_file(".gitignore", "[[:alpha:]]*.txt\n")
        self.create_file("résumé.txt", "ignored")
        self.create_file("123.txt", "kept")
        self.create_file("文档.txt", "ignored")
        
        output = generate_prompt(self.repo_dir, casefold=False)
        self.debug_print_output(output)
        self.assertNotIn("# Path: résumé.txt", output, "résumé.txt should be ignored")
        self.assertNotIn("# Path: 文档.txt", output, "文档.txt should be ignored")
        self.assertIn("# Path: 123.txt", output, "123.txt should be kept")
    
    def test_all_with_casefold(self):
        """
        Test with casefold enabled.
        Root .gitignore contains "IGNORE.TXT". In casefold mode, this rule applies recursively.
        
        Files:
            - "ignore.txt" at root should be ignored.
            - "Special/ignore.txt" should also be ignored.
        
        Expected behavior:
            - Neither the directory tree nor the file contents section should contain any file named "ignore.txt".
        """
        self.create_file(".gitignore", "IGNORE.TXT\n")
        self.create_file("ignore.txt", "ignored")
        self.create_file("Special/ignore.txt", "kept")
        
        output = generate_prompt(self.repo_dir, casefold=True)
        self.debug_print_output(output)
        tree = self.get_tree_section(output)
        # Assert that no line in the tree shows "ignore.txt"
        self.assertNotRegex(tree, r"^[├└]\s+ignore\.txt$", "Root-level ignore.txt should be ignored")
        # Assert that file contents do not show any "# Path:" with ignore.txt.
        self.assertNotIn("# Path: ignore.txt", output, "All ignore.txt files should be ignored in casefold mode")
        self.assertNotIn("# Path: Special/ignore.txt", output, "All ignore.txt files should be ignored in casefold mode")

if __name__ == "__main__":
    unittest.main()
