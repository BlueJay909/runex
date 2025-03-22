#!/usr/bin/env python
import os
import shutil
import tempfile
import unittest
from modules.ignore_logic import GitIgnoreScanner

class IgnoreLogicTest(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for each test.
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def create_file(self, rel_path, content=""):
        path = os.path.join(self.test_dir, rel_path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    def test_basic_ignore(self):
        # Test basic ignore: .gitignore ignoring "ignore.txt"
        self.create_file(".gitignore", "ignore.txt\n")
        self.create_file("keep.txt", "keep")
        self.create_file("ignore.txt", "ignore")
        scanner = GitIgnoreScanner(self.test_dir, casefold=False)
        scanner.load_patterns()
        self.assertTrue(scanner.should_ignore("ignore.txt", False))
        self.assertFalse(scanner.should_ignore("keep.txt", False))

    def test_casefold_ignore(self):
        # Test that casefold mode ignores ".DS_Store" regardless of case.
        self.create_file(".gitignore", ".ds_store\n")
        self.create_file(".DS_Store", "ignored")
        scanner = GitIgnoreScanner(self.test_dir, casefold=True)
        scanner.load_patterns()
        self.assertTrue(scanner.should_ignore(".DS_Store", False))
        self.assertTrue(scanner.should_ignore(".ds_store", False))

    def test_nested_gitignore_negation(self):
        # Root .gitignore ignores "ignore.txt", nested .gitignore unignores in level1/level2.
        self.create_file(".gitignore", "ignore.txt\n")
        self.create_file("level1/ignore.txt", "ignored")
        self.create_file("level1/level2/.gitignore", "!ignore.txt\n")
        self.create_file("level1/level2/ignore.txt", "unignored")
        self.create_file("level1/level2/level3/ignore.txt", "unignored")
        scanner = GitIgnoreScanner(self.test_dir, casefold=False)
        scanner.load_patterns()
        # The file in level1 should be ignored.
        self.assertTrue(scanner.should_ignore("level1/ignore.txt", False))
        # The file in level1/level2 should not be ignored.
        self.assertFalse(scanner.should_ignore("level1/level2/ignore.txt", False))
        # The file in level1/level2/level3 should not be ignored.
        self.assertFalse(scanner.should_ignore("level1/level2/level3/ignore.txt", False))

    def test_posix_brackets(self):
        # Test a rule using POSIX bracket expressions.
        self.create_file(".gitignore", "[[:digit:]].txt\n")
        self.create_file("1.txt", "digit")
        self.create_file("a.txt", "letter")
        scanner = GitIgnoreScanner(self.test_dir, casefold=False)
        scanner.load_patterns()
        self.assertTrue(scanner.should_ignore("1.txt", False))
        self.assertFalse(scanner.should_ignore("a.txt", False))

    def test_unicode_ignore(self):
        # Test ignoring a Unicode file name with casefold.
        self.create_file(".gitignore", "résumé.txt\n")
        self.create_file("résumé.txt", "ignore")
        self.create_file("RÉSUMÉ.TXT", "ignore")
        scanner = GitIgnoreScanner(self.test_dir, casefold=True)
        scanner.load_patterns()
        self.assertTrue(scanner.should_ignore("résumé.txt", False))
        self.assertTrue(scanner.should_ignore("RÉSUMÉ.TXT", False))

if __name__ == "__main__":
    unittest.main()
