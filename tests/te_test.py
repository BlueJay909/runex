"""make all tests"""
import unittest
import tempfile
import os
import subprocess
from git import Repo

from runex.ignore_logic import (
    GitIgnorePattern,
    GitIgnoreScanner
)

from runex.core import (
    generate_prompt,
    generate_folder_structure
)

CASEFOLD = False

# --- Helper Debug Function ---
def debug_patterns(scanner, test_paths, is_dir=False):
    print("DEBUG: Loaded patterns:")
    for idx, pat in enumerate(scanner.patterns):
        regex = pat.regex.pattern if pat.regex else "None"
        print(f"  Pattern {idx}: original={pat.original!r}, regex={regex}")
        for p in test_paths:
            hit = pat.hits(p, is_dir)
            print(f"    hits({p!r}) = {hit}")
    for p in test_paths:
        result = scanner.should_ignore(p, is_dir)
        print(f"DEBUG: should_ignore({p!r}) = {result}")


# --- Tests for GitIgnorePattern ---
class GitIgnorePatternTests(unittest.TestCase):
    def test_translate_component_basic(self):
        pat = GitIgnorePattern("*.txt", "")
        self.assertEqual(pat.translate_component("*.txt"), "[^/]*\\.txt")
    
    def test_match_file(self):
        pat = GitIgnorePattern("foo?.py", "")
        self.assertTrue(pat.hits("foo1.py", False))
        self.assertFalse(pat.hits("foobar.py", False))
    
    def test_match_dir_only(self):
        pat = GitIgnorePattern("build/", "")
        self.assertTrue(pat.hits("build", True))
        self.assertFalse(pat.hits("build", False))
    
    def test_negation(self):
        pat = GitIgnorePattern("!important.log", "")
        # Even if the pattern hits, match() should return False because it’s negated.
        self.assertTrue(pat.hits("important.log", False))
        self.assertFalse(pat.match("important.log", False))
    
    def test_double_star(self):
        pat = GitIgnorePattern("a/**/target.file", "")
        # Should hit even with zero or more directories.
        self.assertTrue(pat.hits("a/target.file", False))
        self.assertTrue(pat.hits("a/b/c/target.file", False))
        self.assertFalse(pat.hits("a/b/c/other.file", False))

    def test_escaped_hash_and_space(self):
        pat = GitIgnorePattern(r"\#notcomment.txt", "")
        self.assertTrue(pat.hits("#notcomment.txt", False))
        pat2 = GitIgnorePattern(r"\ file.txt", "")
        self.assertTrue(pat2.hits(" file.txt", False))

# --- Tests for GitIgnoreScanner ---
class GitIgnoreScannerTests(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        self.repo_path = self.test_dir.name
        Repo.init(self.repo_path)
        self.create_file('.git/config', '[core]\n\trepositoryformatversion = 0\n')
        self.create_file('.git/HEAD', 'ref: refs/heads/main\n')

    def tearDown(self):
        self.test_dir.cleanup()

    def create_file(self, path, content=''):
        full = os.path.join(self.repo_path, path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, 'w') as f:
            f.write(content)

    def create_structure(self, structure):
        for name, content in structure.items():
            full = os.path.join(self.repo_path, name)
            if isinstance(content, dict):
                os.makedirs(full, exist_ok=True)
                self.create_structure({os.path.join(name, k): v for k, v in content.items()})
            else:
                self.create_file(name, content)

    def set_gitignore(self, content):
        self.create_file('.gitignore', content)

    def test_basic_ignore(self):
        structure = {
            'file.txt': 'content',
            'ignore.me': 'content',
            'dir': {
                'subfile.txt': 'content',
                'test.me': 'content'
            },
            'ignored_dir': {
                'dummy.txt': 'content'
            }
        }
        self.create_structure(structure)
        self.set_gitignore("*.me\nignored_dir/\n")
        scanner = GitIgnoreScanner(self.repo_path)
        scanner.load_patterns()
        self.assertTrue(scanner.should_ignore("ignore.me", False))
        self.assertTrue(scanner.should_ignore("dir/test.me", False))
        self.assertTrue(scanner.should_ignore("ignored_dir", True))
        self.assertFalse(scanner.should_ignore("file.txt", False))

    def get_scanner_ignore(self, path, is_dir=False):
        scanner = GitIgnoreScanner(self.repo_path)
        scanner.load_patterns()
        return scanner.should_ignore(path, is_dir)

    def test_nested_gitignores(self):
        structure = {
            'parent': {
                'child': {
                    'file.txt': 'content'
                },
                'ignore.me': 'content'
            }
        }
        self.create_structure(structure)
        self.set_gitignore("parent/*.me\n!parent/child/\n")
        child_gitignore = os.path.join(self.repo_path, 'parent', 'child', '.gitignore')
        os.makedirs(os.path.dirname(child_gitignore), exist_ok=True)
        with open(child_gitignore, 'w') as f:
            f.write("!file.txt\n")
        scanner = GitIgnoreScanner(self.repo_path)
        scanner.load_patterns()
        self.assertFalse(scanner.should_ignore("parent/child/file.txt", False))
        self.assertTrue(scanner.should_ignore("parent/ignore.me", False))

    def test_root_anchor(self):
        structure = {
            'src': {
                'main.c': 'content'
            },
            'build': {
                'src': {
                    'temp': 'content'
                }
            }
        }
        self.create_structure(structure)
        self.set_gitignore("/src/\nbuild/\n")
        scanner = GitIgnoreScanner(self.repo_path)
        scanner.load_patterns()
        self.assertTrue(scanner.should_ignore("src", True))
        self.assertTrue(scanner.should_ignore("build", True))
        # For our prompt generation, we want "build/src" not to be ignored.
        self.assertFalse(scanner.should_ignore("build/src", True))

# --- Tests for Prompt Generation ---
class PromptGenerationTests(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        self.repo_path = self.test_dir.name
        Repo.init(self.repo_path)
        self.create_file('.git/config', '[core]\n\trepositoryformatversion = 0\n')
        self.create_file('.git/HEAD', 'ref: refs/heads/main\n')
    
    def tearDown(self):
        self.test_dir.cleanup()
    
    def create_file(self, path, content=''):
        full = os.path.join(self.repo_path, path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, 'w') as f:
            f.write(content)
    
    def create_structure(self, structure):
        for name, content in structure.items():
            full = os.path.join(self.repo_path, name)
            if isinstance(content, dict):
                os.makedirs(full, exist_ok=True)
                self.create_structure({os.path.join(name, k): v for k, v in content.items()})
            else:
                self.create_file(name, content)
    
    def set_gitignore(self, content):
        self.create_file('.gitignore', content)

    def test_generate_folder_structure(self):
        structure = {
            'src': {
                'main.py': 'print("Hello")',
                'utils': {
                    'helper.py': '# helper'
                }
            },
            'README.md': '# Project'
        }
        self.create_structure(structure)
        self.set_gitignore("# no ignores")
        tree = generate_folder_structure(self.repo_path, CASEFOLD)
        self.assertIn("src/", tree)
        self.assertIn("├── main.py", tree)
        self.assertIn("README.md", tree)
    
    def test_generate_prompt_includes_contents(self):
        structure = {
            'src': {
                'main.py': 'print("Hello World")'
            },
            'data.txt': 'Sample data'
        }
        self.create_structure(structure)
        self.set_gitignore("")
        prompt = generate_prompt(self.repo_path, CASEFOLD)
        self.assertIn("Project Structure:", prompt)
        self.assertIn("src/", prompt)
        self.assertIn('print("Hello World")', prompt)
        self.assertIn("Sample data", prompt)
    
    def test_prompt_with_ignores(self):
        structure = {
            'log': {
                'debug.log': 'debug info',
                'info.log': 'info'
            },
            'src': {
                'main.py': 'print("Running")',
                'temp.tmp': 'temporary'
            },
            'notes.txt': 'remember this'
        }
        self.create_structure(structure)
        self.set_gitignore("*.log\ntemp.tmp\n")
        prompt = generate_prompt(self.repo_path, CASEFOLD)
        self.assertNotIn("debug.log", prompt)
        self.assertNotIn("info.log", prompt)
        self.assertNotIn("temp.tmp", prompt)
        self.assertIn("main.py", prompt)
        self.assertIn("notes.txt", prompt)

# --- Tests for Granular Behaviour ---
class GranularBehaviorTests(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        self.repo_path = self.test_dir.name
        self.repo = Repo.init(self.repo_path)
        self.create_file('.git/config', '[core]\n\trepositoryformatversion = 0\n')
        self.create_file('.git/HEAD', 'ref: refs/heads/main\n')
    
    def tearDown(self):
        self.test_dir.cleanup()
    
    def create_file(self, path, content=''):
        full = os.path.join(self.repo_path, path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, 'w') as f:
            f.write(content)
    
    def create_structure(self, structure):
        for name, content in structure.items():
            full = os.path.join(self.repo_path, name)
            if isinstance(content, dict):
                os.makedirs(full, exist_ok=True)
                self.create_structure({os.path.join(name, k): v for k, v in content.items()})
            else:
                self.create_file(name, content)
    
    def set_gitignore(self, content):
        self.create_file('.gitignore', content)
    
    def run_git_check_ignore(self, path):
        result = subprocess.run(
            ['git', '-C', self.repo_path, 'check-ignore', '-q', path],
            capture_output=True
        )
        return result.returncode == 0
    
    def get_scanner_ignore(self, path, is_dir=False):
        scanner = GitIgnoreScanner(self.repo_path)
        scanner.load_patterns()
        return scanner.should_ignore(path, is_dir)
    
    def test_granular_double_star(self):
        self.create_structure({
            'a': {
                'target.file': 'content',
                'b': {
                    'target.file': 'content',
                    'c': {
                        'target.file': 'content'
                    }
                }
            }
        })
        self.set_gitignore("a/**/target.file\n")
        paths = ["a/target.file", "a/b/target.file", "a/b/c/target.file", "a/b/c/other.file"]
        for p in paths:
            git_ignored = self.run_git_check_ignore(p)
            scanner_ignored = self.get_scanner_ignore(p, False)
            print(f"Double-star test for {p}: Git={git_ignored}, Scanner={scanner_ignored}")
            if p != "a/b/c/other.file":
                self.assertTrue(git_ignored, f"Git should ignore {p}")
                self.assertTrue(scanner_ignored, f"Scanner should ignore {p}")
            else:
                self.assertFalse(git_ignored, f"Git should not ignore {p}")
                self.assertFalse(scanner_ignored, f"Scanner should not ignore {p}")
    
    def test_granular_escaped_pattern(self):
        self.create_structure({
            'test': {
                'file.txt': 'content'
            }
        })
        # Note: Per Git behavior, pattern "test\\file.txt" does NOT match "test/file.txt".
        self.set_gitignore(r"test\\file.txt" + "\n")
        p = "test/file.txt"
        git_ignored = self.run_git_check_ignore(p)
        scanner_ignored = self.get_scanner_ignore(p, False)
        print(f"Escaped pattern test for {p}: Git={git_ignored}, Scanner={scanner_ignored}")
        # Expecting both to be False.
        self.assertFalse(git_ignored, "Git should not ignore test/file.txt with escaped backslash")
        self.assertFalse(scanner_ignored, "Scanner should not ignore test/file.txt with escaped backslash")
    
    def test_granular_prompt_output(self):
        structure = {
            'src': {
                'main.py': 'print("Running")',
                'temp.tmp': 'should be ignored'
            },
            'log': {
                'debug.log': 'debug info'
            },
            'notes.txt': 'remember this'
        }
        self.create_structure(structure)
        self.set_gitignore("*.log\ntemp.tmp\n")
        for f in ["log/debug.log", "src/temp.tmp"]:
            git_ignored = self.run_git_check_ignore(f)
            print(f"Git check-ignore for {f}: {git_ignored}")
            self.assertTrue(git_ignored, f"Git should ignore {f}")
        prompt = generate_prompt(self.repo_path, CASEFOLD)
        print("Generated Prompt:\n", prompt)
        self.assertNotIn("temp.tmp", prompt, "Prompt should not include temp.tmp")
        self.assertNotIn("debug.log", prompt, "Prompt should not include debug.log")
        self.assertIn("main.py", prompt, "Prompt should include main.py")
        self.assertIn("notes.txt", prompt, "Prompt should include notes.txt")
    
    def test_granular_nested_gitignore(self):
        structure = {
            'parent': {
                'child': {
                    'file.txt': 'content',
                    'ignore.me': 'content'
                },
                'ignore.me': 'content'
            }
        }
        self.create_structure(structure)
        self.set_gitignore("parent/*.me\n!parent/child/\n")
        child_gitignore = os.path.join(self.repo_path, 'parent', 'child', '.gitignore')
        os.makedirs(os.path.dirname(child_gitignore), exist_ok=True)
        self.create_file(child_gitignore, "!file.txt\n")
        paths = ["parent/ignore.me", "parent/child/ignore.me", "parent/child/file.txt"]
        for p in paths:
            git_ignored = self.run_git_check_ignore(p)
            scanner_ignored = self.get_scanner_ignore(p, False)
            print(f"Nested gitignore test for {p}: Git={git_ignored}, Scanner={scanner_ignored}")
        self.assertTrue(self.run_git_check_ignore("parent/ignore.me"),
                        "Git should ignore parent/ignore.me")
        self.assertFalse(self.run_git_check_ignore("parent/child/file.txt"),
                         "Git should not ignore parent/child/file.txt")
        self.assertTrue(self.get_scanner_ignore("parent/ignore.me", False),
                        "Scanner should ignore parent/ignore.me")
        self.assertFalse(self.get_scanner_ignore("parent/child/file.txt", False),
                         "Scanner should not ignore parent/child/file.txt")

# --- Tests for Extra Edge Cases Behaviour ---
class ExtraEdgeCasesTests(unittest.TestCase):
    def setUp(self):
        # Create a temporary repository.
        self.test_dir = tempfile.TemporaryDirectory()
        self.repo_path = self.test_dir.name
        self.repo = Repo.init(self.repo_path)
        # Minimal .git setup.
        self.create_file('.git/config', '[core]\n\trepositoryformatversion = 0\n')
        self.create_file('.git/HEAD', 'ref: refs/heads/main\n')
    
    def tearDown(self):
        self.test_dir.cleanup()
    
    def create_file(self, path, content=''):
        full = os.path.join(self.repo_path, path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def create_structure(self, structure):
        """
        Recursively create a file structure from a nested dict.
        """
        for name, content in structure.items():
            full = os.path.join(self.repo_path, name)
            if isinstance(content, dict):
                os.makedirs(full, exist_ok=True)
                self.create_structure({os.path.join(name, k): v for k, v in content.items()})
            else:
                self.create_file(name, content)
    
    def set_gitignore(self, content):
        self.create_file('.gitignore', content)
    
    def run_git_check_ignore(self, path):
        result = subprocess.run(
            ['git', '-C', self.repo_path, 'check-ignore', '-q', path],
            capture_output=True
        )
        return result.returncode == 0

    def get_scanner_ignore(self, path, is_dir=False):
        scanner = GitIgnoreScanner(self.repo_path)
        scanner.load_patterns()
        return scanner.should_ignore(path, is_dir)

    def test_multiple_negations(self):
        # A file that is first ignored then unignored.
        structure = {
            'foo.log': 'log content',
            'bar.log': 'log content'
        }
        self.create_structure(structure)
        # Ignore all .log files, but then unignore foo.log.
        self.set_gitignore("*.log\n!foo.log\n")
        # Git: foo.log should be unignored; bar.log remains ignored.
        self.assertFalse(self.run_git_check_ignore("foo.log"), "Git should not ignore foo.log due to negation")
        self.assertTrue(self.run_git_check_ignore("bar.log"), "Git should ignore bar.log")
        self.assertFalse(self.get_scanner_ignore("foo.log", False), "Scanner should not ignore foo.log")
        self.assertTrue(self.get_scanner_ignore("bar.log", False), "Scanner should ignore bar.log")

    def test_escaped_spaces(self):
        # Files with spaces in the name.
        structure = {
            ' file with space.txt': 'content',  # note the leading space!
            'another file.txt': 'content'
        }
        self.create_structure(structure)
        self.set_gitignore(r"\ file\ with\ space.txt" "\n")
        scanner = GitIgnoreScanner(self.repo_path)
        scanner.load_patterns()
        print("DEBUG for test_escaped_spaces:")
        debug_patterns(scanner, [" file with space.txt", "another file.txt"], is_dir=False)
        self.assertTrue(self.run_git_check_ignore(" file with space.txt"), "Git should ignore ' file with space.txt'")
        self.assertTrue(self.get_scanner_ignore(" file with space.txt", False), "Scanner should ignore ' file with space.txt'")
        self.assertFalse(self.run_git_check_ignore("another file.txt"), "Git should not ignore 'another file.txt'")

    def test_unicode_filenames(self):
        # Files with Unicode characters.
        structure = {
            '文件.txt': '内容',
            '目录': {
                '子文件.txt': '子内容'
            }
        }
        self.create_structure(structure)
        # Ignore all files ending with .txt.
        self.set_gitignore("*.txt\n")
        self.assertTrue(self.run_git_check_ignore("文件.txt"), "Git should ignore Unicode filename 文件.txt")
        self.assertTrue(self.get_scanner_ignore("文件.txt", False), "Scanner should ignore 文件.txt")
        self.assertTrue(self.run_git_check_ignore("目录/子文件.txt"), "Git should ignore 目录/子文件.txt")
        self.assertTrue(self.get_scanner_ignore("目录/子文件.txt", False), "Scanner should ignore 目录/子文件.txt")
    
    def test_trailing_whitespace_in_pattern(self):
        # Patterns with trailing spaces (not escaped) should have the spaces trimmed.
        structure = {
            'spaced.txt': 'content'
        }
        self.create_structure(structure)
        # The pattern "*.txt   " (with trailing spaces) should ignore spaced.txt.
        self.set_gitignore("*.txt   \n")
        self.assertTrue(self.run_git_check_ignore("spaced.txt"), "Git should ignore spaced.txt despite trailing whitespace")
        self.assertTrue(self.get_scanner_ignore("spaced.txt", False), "Scanner should ignore spaced.txt despite trailing whitespace")
    
    def test_ignore_dotfiles(self):
        # Test ignoring hidden files.
        structure = {
            '.env': 'secret',
            '.config': 'data',
            'visible.txt': 'data'
        }
        self.create_structure(structure)
        self.set_gitignore(".*\n")
        self.assertTrue(self.run_git_check_ignore(".env"), "Git should ignore .env")
        self.assertTrue(self.get_scanner_ignore(".env", False), "Scanner should ignore .env")
        self.assertFalse(self.run_git_check_ignore("visible.txt"), "Git should not ignore visible.txt")
    
    def test_complex_combination(self):
        structure = {
            'logs': {
                'error.log': 'error',
                'access.log': 'access'
            },
            'keep': {
                'logs': {
                    'error.log': 'error'
                }
            },
            'other': {
                'logs': {
                    'debug.log': 'debug'
                }
            }
        }
        self.create_structure(structure)
        self.set_gitignore("**/*.log\n!keep/**/*.log\n")
        # Debug output:
        scanner = GitIgnoreScanner(self.repo_path)
        scanner.load_patterns()
        print("DEBUG for test_complex_combination:")
        for path in ["logs/error.log", "keep/logs/error.log", "other/logs/debug.log"]:
            print(f"  For {path}: should_ignore={scanner.should_ignore(path, False)}")
        self.assertTrue(self.run_git_check_ignore("logs/error.log"), "Git should ignore logs/error.log")
        self.assertTrue(self.get_scanner_ignore("logs/error.log", False), "Scanner should ignore logs/error.log")
        self.assertFalse(self.run_git_check_ignore("keep/logs/error.log"), "Git should not ignore keep/logs/error.log")
        self.assertFalse(self.get_scanner_ignore("keep/logs/error.log", False), "Scanner should not ignore keep/logs/error.log")
        self.assertTrue(self.run_git_check_ignore("other/logs/debug.log"), "Git should ignore other/logs/debug.log")
        self.assertTrue(self.get_scanner_ignore("other/logs/debug.log", False), "Scanner should ignore other/logs/debug.log")
        
    def test_deeply_nested_structure(self):
        # Create a very deep nested structure with mixed patterns.
        structure = {"dir" + "/sub" * i: {"file.txt": "content"} for i in range(1, 10)}
        self.create_structure(structure)
        # Ignore any file named file.txt in any subdirectory of "dir".
        self.set_gitignore("dir/**/file.txt\n")
        # All deep file.txt should be ignored.
        for i in range(1, 10):
            path = "dir" + "/sub" * i + "/file.txt"
            self.assertTrue(self.run_git_check_ignore(path), f"Git should ignore {path}")
            self.assertTrue(self.get_scanner_ignore(path, False), f"Scanner should ignore {path}")
    
    def test_prompt_generation_edge(self):
        # Complex prompt generation test: some files ignored, some not.
        structure = {
            'src': {
                'main.py': 'print("Hello World")',
                'ignore.me': 'should be ignored'
            },
            'docs': {
                'README.md': '# Documentation',
                '.secret': 'hidden'
            },
            'temp.tmp': 'temporary',
            '.hidden': 'data'
        }
        self.create_structure(structure)
        # Ignore files ending with .me, temp.tmp, and hidden files.
        self.set_gitignore("*.me\ntemp.tmp\n.*\n")
        prompt = generate_prompt(self.repo_path, CASEFOLD)
        self.assertNotIn("ignore.me", prompt, "Prompt should not include ignore.me")
        self.assertNotIn("temp.tmp", prompt, "Prompt should not include temp.tmp")
        self.assertNotIn(".hidden", prompt, "Prompt should not include .hidden")
        # But docs/README.md and src/main.py should be included.
        self.assertIn("README.md", prompt, "Prompt should include README.md")
        self.assertIn("main.py", prompt, "Prompt should include main.py")

# --- ExtraHardEdgeCasesTests ---
class ExtraHardEdgeCasesTests(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        self.repo_path = self.test_dir.name
        Repo.init(self.repo_path)
        # Minimal Git structure.
        self.create_file('.git/config', '[core]\n\trepositoryformatversion = 0\n')
        self.create_file('.git/HEAD', 'ref: refs/heads/main\n')
    
    def tearDown(self):
        self.test_dir.cleanup()
    
    def create_file(self, path, content=''):
        full = os.path.join(self.repo_path, path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def create_structure(self, structure):
        """Recursively create a file structure from a nested dictionary."""
        for name, content in structure.items():
            full = os.path.join(self.repo_path, name)
            if isinstance(content, dict):
                os.makedirs(full, exist_ok=True)
                self.create_structure({os.path.join(name, k): v for k, v in content.items()})
            else:
                self.create_file(name, content)
    
    def set_gitignore(self, content):
        self.create_file('.gitignore', content)
    
    def run_git_check_ignore(self, path):
        result = subprocess.run(
            ['git', '-C', self.repo_path, 'check-ignore', '-q', path],
            capture_output=True
        )
        return result.returncode == 0
    
    def get_scanner_ignore(self, path, is_dir=False):
        scanner = GitIgnoreScanner(self.repo_path)
        scanner.load_patterns()
        return scanner.should_ignore(path, is_dir)

    def test_complex_negation_and_wildcards(self):
        # A pattern combining wildcards, double-stars, and negation.
        # Ignore all *.tmp files in any subdirectory, but unignore those under "important/".
        structure = {
            'a': {
                'file.tmp': 'temp',
                'b': {
                    'file.tmp': 'temp',
                    'c': {
                        'file.tmp': 'temp',
                        'keep.tmp': 'keep me'
                    }
                }
            },
            'important': {
                'file.tmp': 'important temp'
            }
        }
        self.create_structure(structure)
        self.set_gitignore("**/*.tmp\n!important/**/*.tmp\n")
        
        # Load the scanner and print debug info:
        scanner = GitIgnoreScanner(self.repo_path)
        scanner.load_patterns()
        print("DEBUG for test_complex_negation_and_wildcards:")
        for i, pat in enumerate(scanner.patterns):
            regex = pat.regex.pattern if pat.regex else "None"
            print(f"  Pattern {i}: original={pat.original!r}, regex={regex}")
        for path in ["a/file.tmp", "a/b/c/file.tmp", "important/file.tmp"]:
            result = scanner.should_ignore(path, False)
            print(f"  For {path}: scanner.should_ignore = {result}")
        
        self.assertTrue(self.run_git_check_ignore("a/file.tmp"), "Git should ignore a/file.tmp")
        self.assertTrue(scanner.should_ignore("a/b/c/file.tmp", False), "Scanner should ignore a/b/c/file.tmp")
        self.assertFalse(self.run_git_check_ignore("important/file.tmp"), "Git should not ignore important/file.tmp")
        self.assertFalse(scanner.should_ignore("important/file.tmp", False), "Scanner should not ignore important/file.tmp")

    def test_mixed_wildcards_character_class(self):
        self.create_structure({
            'log10.txt': 'should be ignored',   # Matches log[0-9]?.txt (digit '1', then '0')
            'log1a.txt': 'should be ignored',   # Matches log[0-9]?.txt (digit '1', then 'a')
            'log1.txt': 'should NOT be ignored',# Does NOT match (no character after '1')
            'log12.txt': 'should be ignored'    # Matches log[0-9]?.txt (digit '1', then '2')
        })
        self.set_gitignore("log[0-9]?.txt\n")
        self.assertTrue(self.run_git_check_ignore("log10.txt"))
        self.assertTrue(self.run_git_check_ignore("log1a.txt"))
        self.assertFalse(self.run_git_check_ignore("log1.txt"))  # Corrected expectation
        self.assertTrue(self.run_git_check_ignore("log12.txt"))

    def test_escaped_and_mixed_spaces(self):
        # Test a complex filename with spaces and escaped spaces.
        structure = {
            ' my file.txt': 'data1',  # note the leading space!
            'my  file.txt': 'data2',   # double space between 'my' and 'file'
            'normal.txt': 'data3'
        }
        self.create_structure(structure)
        # Write a .gitignore pattern that escapes a space so that it matches " my file.txt" (with a leading space).
        self.set_gitignore(r"\ my file.txt" "\n")
        scanner = GitIgnoreScanner(self.repo_path)
        scanner.load_patterns()
        print("DEBUG for test_escaped_and_mixed_spaces:")
        debug_patterns(scanner, [" my file.txt", "my  file.txt", "normal.txt"], is_dir=False)
        self.assertTrue(self.run_git_check_ignore(" my file.txt"), "Git should ignore ' my file.txt'")
        self.assertTrue(self.get_scanner_ignore(" my file.txt", False), "Scanner should ignore ' my file.txt'")
        self.assertFalse(self.run_git_check_ignore("my  file.txt"), "Git should not ignore 'my  file.txt'")
        self.assertFalse(self.get_scanner_ignore("normal.txt", False), "Git should not ignore 'normal.txt'")

    def test_deeply_complex_structure(self):
        """
        Test nested .gitignore behavior.
        Here the root .gitignore ignores "ignore.txt" everywhere.
        A nested .gitignore in level1/level2 unignores "ignore.txt" in that directory.
        On our system, git check-ignore does not ignore files in deeper subdirectories of level1/level2.
        """
        structure = {
            'level1': {
                'keep.txt': 'important',
                'ignore.txt': 'not important',
                'level2': {
                    'keep.txt': 'important',
                    'ignore.txt': 'not important',
                    'level3': {
                        'keep.txt': 'important',
                        'ignore.txt': 'not important'
                    }
                }
            }
        }
        self.create_structure(structure)
        self.set_gitignore("ignore.txt\n")
        nested_ignore = os.path.join(self.repo_path, "level1", "level2", ".gitignore")
        os.makedirs(os.path.dirname(nested_ignore), exist_ok=True)
        self.create_file(nested_ignore, "!ignore.txt\n")
        scanner = GitIgnoreScanner(self.repo_path)
        scanner.load_patterns()
        print("DEBUG for test_deeply_complex_structure:")
        for path in ["level1/ignore.txt", "level1/level2/ignore.txt", "level1/level2/level3/ignore.txt"]:
            regexes = [pat.regex.pattern for pat in scanner.patterns if pat.original.lower().strip("!") == "ignore.txt"]
            print(f"  For {path}: regexes={regexes}, scanner.should_ignore={scanner.should_ignore(path, False)}")
        self.assertTrue(self.run_git_check_ignore("level1/ignore.txt"), "Git should ignore level1/ignore.txt")
        self.assertFalse(self.run_git_check_ignore("level1/level2/ignore.txt"), "Git should not ignore level1/level2/ignore.txt")
        # Adjust expectation based on actual git behavior:
        self.assertFalse(self.run_git_check_ignore("level1/level2/level3/ignore.txt"), "Git should not ignore level1/level2/level3/ignore.txt")
        
    def test_extremely_complex_pattern(self):
        # Test a pattern with multiple wildcards, character classes, and negation combined.
        structure = {
            'data': {
                'temp1.log': 'a',
                'temp2.log': 'b',
                'final.log': 'c',
                'notes.txt': 'd'
            },
            'backup': {
                'temp1.log': 'a',
                'final.log': 'c'
            }
        }
        self.create_structure(structure)
        # Pattern explanation:
        # - Ignore any file in "data/" that matches "temp[0-9].log"
        # - But do not ignore files that contain "final"
        self.set_gitignore("data/temp[0-9].log\n!data/*final.log\n")
        self.assertTrue(self.run_git_check_ignore("data/temp1.log"), "Should ignore data/temp1.log")
        self.assertTrue(self.get_scanner_ignore("data/temp2.log", False), "Scanner should ignore data/temp2.log")
        self.assertFalse(self.run_git_check_ignore("data/final.log"), "Should not ignore data/final.log")
        self.assertFalse(self.get_scanner_ignore("backup/temp1.log", False), "Backup files not in data/ should not be ignored")
    

if __name__ == '__main__':
    unittest.main(failfast=True, verbosity=2)
