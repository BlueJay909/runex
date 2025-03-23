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
        # Create a temporary directory for each test.
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
        'structure' is a dict: keys are names; values are either a string (file content)
        or a dict (subdirectory).
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
    
    def get_tree_section(self, prompt_output):
        """
        Extract the folder tree section from the generated prompt.
        Assumes the prompt is formatted as:
          Project Structure:
          
          <tree>
          
          <file contents>
        """
        parts = prompt_output.split("\n\n")
        if len(parts) >= 2:
            return parts[1]
        return ""
    
    def debug_print_tree(self, prompt_output):
        tree = self.get_tree_section(prompt_output)
        print("DEBUG: Directory Tree:")
        print(tree)
        return tree

    def test_extremely_deep_nested(self):
        """
        Create a 10-level nested structure.
          - At every level, a file named "junk.tmp" is created.
          - At level 5 and deeper, a file named "keep.tmp" is also created.
        Root .gitignore ignores "*.tmp".
        A nested .gitignore at level5 unignores "keep.tmp".
        
        Expected behavior:
          - All "junk.tmp" files are ignored.
          - "keep.tmp" files in level5 and deeper are unignored.
        """
        deep = {}
        current = deep
        for i in range(1, 11):
            folder = f"level{i}"
            current[folder] = {}
            # Create a file that should always be ignored.
            current[folder]["junk.tmp"] = f"junk at level {i}"
            if i >= 5:
                # Create a file that should be unignored starting at level5.
                current[folder]["keep.tmp"] = f"keep at level {i}"
            current = current[folder]
        
        self.create_structure(deep)
        # Root .gitignore ignores all *.tmp files.
        self.create_file(".gitignore", "*.tmp\n")
        # Nested .gitignore in level5 unignores keep.tmp files.
        self.create_file("level1/level2/level3/level4/level5/.gitignore", "!keep.tmp\n")
        
        output = generate_prompt(self.repo_dir, casefold=False)
        tree = self.debug_print_tree(output)
        # Expect no line at root for "junk.tmp"
        self.assertNotRegex(tree, r"^[├└]\s+junk\.tmp$", "Root junk.tmp should be ignored")
        # Expect that in level5 or deeper, "keep.tmp" appears.
        self.assertRegex(tree, r"level1/level2/level3/level4/level5/.*[├└].*keep\.tmp", "keep.tmp in level5 should be unignored")
    
    def test_complex_wildcards_and_posix(self):
        """
        Root .gitignore:
            - Ignores files matching pattern: "temp*[0-9].txt"
            - Unignores files matching: "temp[[:digit:]]_keep.txt"
        
        Files created:
            - "temp123.txt" (should be ignored)
            - "temp9.txt"   (should be ignored)
            - "temp5_keep.txt" (should be unignored)
            - "tempx.txt"   (should not match the ignore rule and be kept)
        
        Expected behavior:
            - "temp123.txt" and "temp9.txt" are ignored.
            - "temp5_keep.txt" is unignored.
            - "tempx.txt" is kept.
        """
        self.create_file(".gitignore", "temp*[0-9].txt\n!temp[[:digit:]]_keep.txt\n")
        self.create_file("temp123.txt", "ignored")
        self.create_file("temp9.txt", "ignored")
        self.create_file("temp5_keep.txt", "kept")
        self.create_file("tempx.txt", "not ignored")
        
        output = generate_prompt(self.repo_dir, casefold=False)
        tree = self.debug_print_tree(output)
        self.assertNotRegex(tree, r"^[├└]\s+temp123\.txt$", "temp123.txt should be ignored")
        self.assertNotRegex(tree, r"^[├└]\s+temp9\.txt$", "temp9.txt should be ignored")
        self.assertRegex(tree, r"temp[\\/]{1}temp5_keep\.txt", "temp5_keep.txt should be unignored")
        self.assertRegex(tree, r"^[├└]\s+tempx\.txt$", "tempx.txt should be kept")
    
    def test_negations_conflicting_rules(self):
        """
        Root .gitignore:
            - Ignores all ".log" files.
            - Unignores files matching "debug/*.log".
        
        Files created:
            - "app.log" at the root (should be ignored).
            - "debug/app.log" (should be unignored).
        
        Expected behavior:
            - Root-level "app.log" is ignored.
            - "debug/app.log" appears in the structure.
        """
        self.create_file(".gitignore", "*.log\n!debug/*.log\n")
        self.create_file("app.log", "ignored")
        self.create_file("debug/app.log", "kept")
        
        output = generate_prompt(self.repo_dir, casefold=False)
        tree = self.debug_print_tree(output)
        self.assertNotRegex(tree, r"^[├└]\s+app\.log$", "Root app.log should be ignored")
        self.assertRegex(tree, r"debug[\\/].*app\.log", "debug/app.log should be unignored")

    def test_deep_structure_without_nested_gitignore_with_negation(self):
        """
        Root .gitignore:
            - Ignores all ".tmp" files.
            - Unignores files matching "include/*.tmp".
        
        Files:
            - "app.tmp" at the root (ignored).
            - "include/app.tmp" (unignored).
        """
        self.create_file(".gitignore", "*.tmp\n!include/*.tmp\n")
        self.create_file("app.tmp", "ignored")
        self.create_file("include/app.tmp", "kept")
        
        output = generate_prompt(self.repo_dir, casefold=False)
        tree = self.debug_print_tree(output)
        self.assertNotRegex(tree, r"^[├└]\s+app\.tmp$", "Root app.tmp should be ignored")
        self.assertRegex(tree, r"include[\\/].*app\.tmp", "include/app.tmp should be unignored")

    # Fails because [[:alpha:]] still falls back to ASCII
    def test_unicode_and_special_characters(self):
        """
        Create a structure with Unicode file/folder names and special characters.
        Root .gitignore ignores files starting with a Unicode letter via a POSIX bracket.
        
        Files created:
            - "résumé.txt" (should be ignored because it starts with a letter)
            - "123.txt" (should be kept because it doesn't start with a letter)
            - "文档.txt" (should be ignored because it starts with a letter)
        
        Expected behavior:
            - "résumé.txt" and "文档.txt" are ignored.
            - "123.txt" is kept.
        """
        self.create_file(".gitignore", "[[:alpha:]]*.txt\n")
        self.create_file("résumé.txt", "ignored")
        self.create_file("123.txt", "kept")
        self.create_file("文档.txt", "ignored")
        
        output = generate_prompt(self.repo_dir, casefold=False)
        tree = self.debug_print_tree(output)
        # We assume that in WM_UNICODE mode, POSIX classes match Unicode letters.
        self.assertNotRegex(tree, r"^[├└].*résumé\.txt$", "résumé.txt should be ignored")
        self.assertNotRegex(tree, r"^[├└].*文档\.txt$", "文档.txt should be ignored")
        self.assertRegex(tree, r"^[├└]\s+123\.txt$", "123.txt should be kept")
    
    def test_all_with_casefold(self):
        """
        Test with casefold enabled.
        Root .gitignore contains "IGNORE.TXT". In casefold mode, this rule applies recursively.
        
        Files:
            - "ignore.txt" at root should be ignored.
            - "Special/ignore.txt" should also be ignored.
        
        Expected behavior:
            - No file named "ignore.txt" appears anywhere in the directory tree.
        """
        self.create_file(".gitignore", "IGNORE.TXT\n")
        self.create_file("ignore.txt", "ignored")
        self.create_file("Special/ignore.txt", "kept")
        
        output = generate_prompt(self.repo_dir, casefold=True)
        tree = self.debug_print_tree(output)
        # Assert that no root-level file exactly matching "ignore.txt" appears.
        self.assertNotRegex(tree, r"^[├└]\s+ignore\.txt$", "Root ignore.txt should be ignored")
        # Also ensure that no file named "ignore.txt" appears anywhere.
        self.assertNotRegex(tree, r"ignore\.txt", "All ignore.txt files should be ignored in casefold mode")
    
if __name__ == "__main__":
    unittest.main()
