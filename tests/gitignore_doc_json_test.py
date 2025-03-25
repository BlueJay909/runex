#!/usr/bin/env python
"""
Advanced tests for runex (formerly prompt_generator.py) against official .gitignore rules.

These tests create temporary directory trees and .gitignore files according to
the official .gitignore pattern format. They then run the runex CLI tool in JSON mode
(with --only-structure) and compare the parsed directory structure (as a nested JSON object)
against the expected structure.

Each test case is commented with the expected behavior.
"""

import os
import json
import unittest
import tempfile
import shutil
import subprocess
import sys

def run_prompt_generator(root_dir: str, extra_args=None) -> dict:
    """
    Run the runex CLI on the given root directory with --json and --only-structure
    plus any extra_args, and return the parsed JSON object.
    """
    if extra_args is None:
        extra_args = []
    cmd = [
        sys.executable,
        "-m",
        "runex.cli",
        root_dir,
        "--json",
        "--only-structure"
    ] + extra_args
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"runex.cli failed: {proc.stderr}")
    try:
        result = json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        raise ValueError(f"Output is not valid JSON:\n{proc.stdout}\nError: {e}")
    return result

class AdvancedGitignoreTest(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.root = self.temp_dir

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def create_file(self, rel_path: str, content: str):
        full_path = os.path.join(self.root, rel_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)

    def create_gitignore(self, rel_path: str, content: str):
        self.create_file(rel_path, content)

    def get_tree(self, data: dict) -> dict:
        """
        Returns the 'structure' part of the JSON output.
        """
        return data.get("structure", {})

    # --- Test cases based on official .gitignore documentation ---

    def test_blank_lines_and_comments(self):
        """
        Test that blank lines and lines starting with '#' are ignored.
        
        .gitignore content:
          (a blank line)
          # This is a comment
          \#Not a comment.txt
        
        Files:
          - "#Not a comment.txt" should be ignored (because the backslash escapes the hash)
          - "file.txt" should be included.
        
        Expected structure:
          Root should contain:
            - .gitignore
            - file.txt
        """
        content = "\n# This is a comment\n\\#Not a comment.txt\n"
        self.create_gitignore(".gitignore", content)
        self.create_file("file.txt", "keep")
        self.create_file("#Not a comment.txt", "ignore me")
        
        data = run_prompt_generator(self.root)
        # In the structure, we expect .gitignore and file.txt only.
        children = sorted(child["name"] for child in self.get_tree(data)["children"])
        self.assertEqual(children, [".gitignore", "file.txt"],
                         "Blank lines and comments: '#Not a comment.txt' should be treated as a literal and ignored by the rule.")

    def test_trailing_spaces(self):
        """
        Trailing spaces in .gitignore are ignored unless escaped.
        
        .gitignore:
          "ignore.txt   " (with trailing spaces, not escaped)
          "\ ignore2.txt" (escaped space, should be taken literally)
        
        Files:
          - "ignore.txt" should match the first rule and be ignored.
          - " ignore2.txt" (with a leading space) should be ignored because the escaped space means literal space.
          - "keep.txt" should be kept.
        """
        self.create_gitignore(".gitignore", "ignore.txt   \n\\ ignore2.txt\n")
        self.create_file("ignore.txt", "should ignore")
        self.create_file(" ignore2.txt", "should ignore too")
        self.create_file("keep.txt", "keep")
        
        data = run_prompt_generator(self.root)
        # The top-level should list .gitignore and keep.txt (ignore.txt and " ignore2.txt" should be ignored)
        children = [child["name"] for child in self.get_tree(data)["children"]]
        self.assertNotIn("ignore.txt", children, "Trailing spaces: ignore.txt should be ignored")
        self.assertIn("keep.txt", children, "Trailing spaces: keep.txt should be kept")
        self.assertNotIn(" ignore2.txt", children, "Escaped space: file ' ignore2.txt' should be ignored")

    def test_negation_unignore(self):
        """
        Test negation: A .gitignore rule can start with "!" to re-include files.
        
        .gitignore at root:
          ignore.txt
          !ignore.txt
        
        Files:
          - "ignore.txt" should ultimately be unignored.
        
        Expected: The directory structure should include ignore.txt.
        """
        self.create_gitignore(".gitignore", "ignore.txt\n!ignore.txt\n")
        self.create_file("ignore.txt", "content")
        
        data = run_prompt_generator(self.root)
        children = [child["name"] for child in self.get_tree(data)["children"]]
        self.assertIn("ignore.txt", children, "Negation: ignore.txt should be unignored by the ! rule")

    def test_leading_slash(self):
        """
        Patterns with a leading slash are relative to the .gitignore file's location.
        
        .gitignore at root:
          /foo.txt
        
        Files:
          - "foo.txt" at the root should be ignored.
          - "sub/foo.txt" should not be ignored.
        """
        self.create_gitignore(".gitignore", "/foo.txt\n")
        self.create_file("foo.txt", "ignore")
        self.create_file("sub/foo.txt", "keep")
        
        data = run_prompt_generator(self.root)
        children = [child["name"] for child in self.get_tree(data)["children"]]
        # At root we expect .gitignore and sub (foo.txt is ignored)
        self.assertEqual(sorted(children), [".gitignore", "sub"],
                         "Leading slash: foo.txt at root should be ignored, sub/foo.txt should be kept")

    def test_trailing_slash_directory_only(self):
        """
        A pattern ending with a slash matches directories only.
        
        .gitignore:
          logs/
        
        Files:
          - "logs" (a directory) should be ignored.
          - "logs.txt" should be kept.
        """
        self.create_gitignore(".gitignore", "logs/\n")
        os.makedirs(os.path.join(self.root, "logs"), exist_ok=True)
        self.create_file("logs.txt", "keep")
        self.create_file("logs/file.log", "ignore")
        
        data = run_prompt_generator(self.root)
        children = [child["name"] for child in self.get_tree(data)["children"]]
        self.assertNotIn("logs", children, "Trailing slash: directory 'logs' should be ignored")
        self.assertIn("logs.txt", children, "logs.txt should be kept")

    def test_single_star_behavior(self):
        """
        Test that '*' matches any characters except '/'.
        
        .gitignore:
          *.tmp
        
        Files:
          - "a.tmp" should be ignored.
          - "folder/a.tmp" should NOT be ignored (because '*' does not match across '/').
        """
        self.create_gitignore(".gitignore", "*.tmp\n")
        self.create_file("a.tmp", "ignore")
        self.create_file("folder/a.tmp", "keep")
        
        data = run_prompt_generator(self.root)
        children = [child["name"] for child in self.get_tree(data)["children"]]
        self.assertIn("folder", children, "Folder should appear since its file is not ignored")
        self.assertNotIn("a.tmp", children, "a.tmp at root should be ignored")

    def test_double_star_recursive(self):
        """
        Test that '**' can match across directories.
        
        .gitignore:
          **/temp.txt
        
        Files:
          - "temp.txt" at root should be ignored.
          - "sub/temp.txt" should be ignored.
          - "sub/dir/temp.txt" should be ignored.
        """
        self.create_gitignore(".gitignore", "**/temp.txt\n")
        self.create_file("temp.txt", "ignore")
        self.create_file("sub/temp.txt", "ignore")
        self.create_file("sub/dir/temp.txt", "ignore")
        
        data = run_prompt_generator(self.root)
        # Since all temp.txt files are ignored, they shouldn't appear in the structure.
        def find_file(node, filename):
            if node["name"] == filename:
                return True
            for child in node.get("children", []):
                if find_file(child, filename):
                    return True
            return False

        tree = self.get_tree(data)
        self.assertFalse(find_file(tree, "temp.txt"),
                         "All temp.txt files should be ignored with **/temp.txt rule")

if __name__ == "__main__":
    unittest.main()
