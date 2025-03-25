import unittest
import os
import tempfile
from codetext.wildmatch import wildmatch, WM_MATCH, WM_NOMATCH, WM_CASEFOLD, WM_PATHNAME, WM_UNICODE

# Assuming the original code is in a module named 'gitignore_utils'
from codetext.ignore_logic import GitIgnorePattern, GitIgnoreScanner

class TestGitIgnorePattern(unittest.TestCase):
    def setUp(self):
        self.source_dir = ""
        self.casefold = False

    def test_basic_pattern(self):
        pattern = GitIgnorePattern("*.py", self.source_dir, self.casefold)
        self.assertTrue(pattern.match("script.py", False))
        self.assertFalse(pattern.match("README.md", False))

    def test_directory_only(self):
        pattern = GitIgnorePattern("build/", self.source_dir, self.casefold)
        self.assertTrue(pattern.match("build", True))
        self.assertFalse(pattern.match("build", False))  # Not a directory
        self.assertFalse(pattern.match("build/file", True))  # File inside directory

    def test_negation(self):
        pattern = GitIgnorePattern("!important.txt", self.source_dir, self.casefold)
        # hits() should match the file name, but match() should return False (meaning it’s unignored).
        self.assertTrue(pattern.hits("important.txt", False))
        self.assertFalse(pattern.match("important.txt", False))

    def test_slash_pattern(self):
        pattern = GitIgnorePattern("src/*.c", self.source_dir, self.casefold)
        self.assertTrue(pattern.match("src/main.c", False))
        self.assertFalse(pattern.match("lib/main.c", False))

    def test_casefold(self):
        pattern = GitIgnorePattern("IMAGE.PNG", "", casefold=True)
        self.assertTrue(pattern.match("image.png", False))
        self.assertTrue(pattern.match("IMAGE.PNG", False))

    def test_double_asterisk(self):
        pattern = GitIgnorePattern("**/test", self.source_dir, self.casefold)
        self.assertTrue(pattern.match("unit/test", False))
        self.assertTrue(pattern.match("integration/test", False))
        self.assertTrue(pattern.match("test", False))

    def test_bracket_expression(self):
        pattern = GitIgnorePattern("[a-z].txt", self.source_dir, self.casefold)
        self.assertTrue(pattern.match("a.txt", False))
        self.assertFalse(pattern.match("1.txt", False))

class TestGitIgnoreScanner(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root_dir = self.temp_dir.name
        self.scanner = GitIgnoreScanner(self.root_dir)

    def tearDown(self):
        self.temp_dir.cleanup()

    def create_structure(self, structure):
        for path, content in structure.items():
            full_path = os.path.join(self.root_dir, path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'w') as f:
                f.write(content)

    def test_basic_ignore(self):
        structure = {
            '.gitignore': '*.log\n!important.log',
            'error.log': '',
            'important.log': ''
        }
        self.create_structure(structure)
        self.scanner.load_patterns()
        self.assertTrue(self.scanner.should_ignore('error.log'))
        self.assertFalse(self.scanner.should_ignore('important.log'))

    def test_nested_gitignore(self):
        structure = {
            'sub/.gitignore': '*.tmp',
            'sub/file.tmp': '',
            'sub/docs/note.txt': ''
        }
        self.create_structure(structure)
        self.scanner.load_patterns()
        self.assertTrue(self.scanner.should_ignore('sub/file.tmp'))
        self.assertFalse(self.scanner.should_ignore('sub/docs/note.txt'))

    def test_override_pattern(self):
        structure = {
            '.gitignore': '*.bak',
            'data/.gitignore': '!important.bak',
            'data/important.bak': ''
        }
        self.create_structure(structure)
        self.scanner.load_patterns()
        self.assertTrue(self.scanner.should_ignore('file.bak'))
        self.assertFalse(self.scanner.should_ignore('data/important.bak'))

class TestWildMatch(unittest.TestCase):
    def test_basic_wildcards(self):
        self.assertEqual(wildmatch("*.txt", "file.txt", 0), WM_MATCH)
        self.assertEqual(wildmatch("file?", "file1", 0), WM_MATCH)
        self.assertEqual(wildmatch("file?", "file", 0), WM_NOMATCH)

    def test_pathname_flag(self):
        # With WM_PATHNAME, * shouldn't match /
        self.assertEqual(wildmatch("src/*.c", "src/main.c", WM_PATHNAME), WM_MATCH)
        self.assertEqual(wildmatch("src/*.c", "src/sub/main.c", WM_PATHNAME), WM_NOMATCH)

    def test_casefold_flag(self):
        self.assertEqual(wildmatch("FILE", "file", WM_CASEFOLD), WM_MATCH)
        self.assertEqual(wildmatch("FILE", "file", 0), WM_NOMATCH)

    def test_bracket_expressions(self):
        self.assertEqual(wildmatch("[!a-z]", "A", 0), WM_MATCH)

    def test_double_asterisk(self):
        self.assertEqual(wildmatch("**/test", "sub/dir/test", 0), WM_MATCH)
        self.assertEqual(wildmatch("a/**/b", "a/x/y/b", 0), WM_MATCH)

    def test_escaped_characters(self):
        self.assertEqual(wildmatch("\\*", "*", 0), WM_MATCH)
        self.assertEqual(wildmatch("\\[a\\]", "[a]", 0), WM_MATCH)

    def test_posix_classes_unicode(self):
        self.assertEqual(wildmatch("[[:lower:]]", "k", WM_UNICODE), WM_MATCH)
        self.assertEqual(wildmatch("[[:upper:]]", "K", WM_UNICODE | WM_CASEFOLD), WM_MATCH)

if __name__ == '__main__':
    unittest.main()