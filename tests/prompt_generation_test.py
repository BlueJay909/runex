#!/usr/bin/env python
import os
import shutil
import tempfile
import unittest
from codetext.core import generate_prompt

class PromptGenerationTest(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def create_file(self, rel_path, content=""):
        path = os.path.join(self.test_dir, rel_path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    def test_basic_structure(self):
        # Basic structure: .gitignore ignores "ignore.txt".
        self.create_file(".gitignore", "ignore.txt\n")
        self.create_file("keep.txt", "keep")
        self.create_file("ignore.txt", "ignore")
        output = generate_prompt(self.test_dir, casefold=False)
        self.assertIn("keep.txt", output)
        self.assertNotIn("ignore.txt", output)

    def test_deep_structure_with_nested_gitignore(self):
        # Deep structure with nested .gitignore: root ignores "ignore.txt", nested unignores in level1/level2.
        self.create_file(".gitignore", "ignore.txt\n")
        self.create_file("level1/ignore.txt", "ignored")
        self.create_file("level1/level2/.gitignore", "!ignore.txt\n")
        self.create_file("level1/level2/ignore.txt", "unignored")
        self.create_file("level1/level2/level3/ignore.txt", "unignored")
        output = generate_prompt(self.test_dir, casefold=False)
        self.assertNotIn("level1/ignore.txt", output)
        self.assertIn("level1/level2/ignore.txt", output)
        self.assertIn("level1/level2/level3/ignore.txt", output)

    def test_deep_structure_without_nested_gitignore_with_negation(self):
        # Root .gitignore ignores all .log files, but uses negation for a specific folder.
        self.create_file(".gitignore", "*.log\n!special/*.log\n")
        self.create_file("app.log", "ignored")
        self.create_file("special/app.log", "kept")
        output = generate_prompt(self.test_dir, casefold=False)
        # Assert that there is no line in the tree output that indicates a root-level file "app.log"
        self.assertNotRegex(output, r"^[├└]── app\.log$", "Root app.log should be ignored")
        self.assertIn("special/app.log", output)

    def test_special_characters(self):
        # Test wildcards and special characters.
        self.create_file(".gitignore", "*.log\n")
        self.create_file("test.log", "log file")
        self.create_file("test.txt", "text file")
        output = generate_prompt(self.test_dir, casefold=False)
        self.assertNotIn("test.log", output)
        self.assertIn("test.txt", output)

    def test_unicode_structure(self):
        # Test deep structure with Unicode file names.
        self.create_file(".gitignore", "résumé.txt\n")
        self.create_file("résumé.txt", "ignore this")
        self.create_file("doc/notes.txt", "keep these")
        output = generate_prompt(self.test_dir, casefold=True)
        self.assertNotIn("résumé.txt", output)
        self.assertIn("notes.txt", output)

if __name__ == "__main__":
    unittest.main()
