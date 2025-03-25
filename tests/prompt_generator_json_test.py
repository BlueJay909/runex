#!/usr/bin/env python
"""
Unit tests for the codetext CLI tool in JSON mode (JSON output, --only-structure),
using a temporary filesystem to compare actual vs. expected.
"""

import unittest
import tempfile
import os
import shutil
import subprocess
import json
import sys

class TestPromptGeneratorJsonOnlyStructure(unittest.TestCase):
    def setUp(self):
        # Create a temp directory for each test
        self.tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        # Remove the temp directory
        shutil.rmtree(self.tmp_dir)

    def _run_prompt_generator(self, extra_args=None):
        """
        Helper to run prompt_generator.py with --json --only-structure plus any extra_args,
        capturing stdout and returning the parsed JSON.
        """
        if extra_args is None:
            extra_args = []
        cmd = [
            sys.executable,
            "-m",
            "codetext.cli",
            self.tmp_dir,
            "--json",
            "--only-structure"
        ] + extra_args
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(proc.returncode, 0, f"Prompt generator failed: {proc.stderr}")
        try:
            data = json.loads(proc.stdout)
        except json.JSONDecodeError as e:
            self.fail(f"Output is not valid JSON. Output:\n{proc.stdout}\nError: {e}")
        return data

    def create_file(self, rel_path, content):
        """
        Helper to create a file with content in self.tmp_dir,
        automatically creating parent folders as needed.
        """
        full_path = os.path.join(self.tmp_dir, rel_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)

    def create_gitignore(self, rel_path, content):
        self.create_file(rel_path, content)

    def test_basic_no_ignore(self):
        """
        A basic structure with no .gitignore. 
        We expect the JSON output to have 'structure' with all files/folders,
        and no 'files' key since we used --only-structure.
        """
        self.create_file("folderA/file1.txt", "content1")
        self.create_file("folderA/file2.txt", "content2")
        self.create_file("file3.txt", "content3")

        # Run
        data = self._run_prompt_generator()

        # The 'structure' key should be present, 'files' absent (because --only-structure).
        self.assertIn("structure", data)
        self.assertNotIn("files", data)

        # Check the top-level name is the actual base name.
        base_name = os.path.basename(os.path.abspath(self.tmp_dir))
        self.assertEqual(data["structure"]["name"], base_name)

        # We expect children: folderA, file3.txt
        # And inside folderA: file1.txt, file2.txt
        top_children = sorted(child["name"] for child in data["structure"]["children"])
        self.assertEqual(top_children, ["file3.txt", "folderA"])

        folderA_node = next(child for child in data["structure"]["children"] if child["name"] == "folderA")
        folderA_kids = sorted(c["name"] for c in folderA_node["children"])
        self.assertEqual(folderA_kids, ["file1.txt", "file2.txt"])

    def test_ignore_specific_file(self):
        """
        .gitignore with 'ignore.txt' at the root, we also have 'keep.txt'.
        Then we run --only-structure --json, ignoring ignore.txt.
        """
        self.create_gitignore(".gitignore", "ignore.txt\n")
        self.create_file("ignore.txt", "ignored content")
        self.create_file("keep.txt", "keep content")

        data = self._run_prompt_generator()

        # Expect no "files" key, structure has .gitignore and keep.txt
        self.assertIn("structure", data)
        self.assertNotIn("files", data)

        base_name = os.path.basename(os.path.abspath(self.tmp_dir))
        self.assertEqual(data["structure"]["name"], base_name)

        # Children should be [".gitignore", "keep.txt"], ignoring "ignore.txt"
        top_children = sorted(child["name"] for child in data["structure"]["children"])
        self.assertEqual(top_children, [".gitignore", "keep.txt"])

    def test_nested_ignore(self):
        """
        Root .gitignore: "ignore.txt"
        folder1/.gitignore: "!ignore.txt" (unignore)
        folder1/ignore.txt => unignored
        folder1/sub/ignore.txt => also unignored
        """
        self.create_gitignore(".gitignore", "ignore.txt\n")
        self.create_gitignore("folder1/.gitignore", "!ignore.txt\n")
        self.create_file("folder1/ignore.txt", "unignored@folder1")
        self.create_file("folder1/sub/ignore.txt", "unignored@sub")

        data = self._run_prompt_generator()

        # Expect .gitignore in root and folder1, plus the sub folder, ignoring at the top
        self.assertIn("structure", data)

        # Root children: ".gitignore", "folder1"
        root_children = sorted(c["name"] for c in data["structure"]["children"])
        self.assertEqual(root_children, [".gitignore", "folder1"])

        folder1 = next(c for c in data["structure"]["children"] if c["name"] == "folder1")
        folder1_children = sorted(ch["name"] for ch in folder1["children"])
        # folder1 has ".gitignore", "ignore.txt", "sub"
        self.assertEqual(folder1_children, [".gitignore", "ignore.txt", "sub"])

        sub = next(ch for ch in folder1["children"] if ch["name"] == "sub")
        sub_children = sorted(n["name"] for n in sub["children"])
        self.assertEqual(sub_children, ["ignore.txt"])

    def test_casefold_root_ignore(self):
        """
        .gitignore: "IGNORE.txt"
        We have "ignore.txt" (should be ignored if casefold is on)
        We have "keep.txt"
        We pass --casefold => ignoring "ignore.txt"
        """
        self.create_gitignore(".gitignore", "IGNORE.txt\n")
        self.create_file("ignore.txt", "something")
        self.create_file("keep.txt", "something2")

        # We'll pass an extra arg: --casefold
        data = self._run_prompt_generator(extra_args=["--casefold"])

        # No "files" key in the JSON, because --only-structure was used
        self.assertIn("structure", data)
        top_children = sorted(c["name"] for c in data["structure"]["children"])
        self.assertEqual(top_children, [".gitignore", "keep.txt"])

    def test_relative_root(self):
        """
        If we pass --relative-root, the structure's top "name" should be "."
        """
        self.create_file("folderX/stuff.txt", "stuff")

        data = self._run_prompt_generator(extra_args=["--relative-root"])
        self.assertIn("structure", data)
        self.assertEqual(data["structure"]["name"], ".")

    def test_deep_structure(self):
        """
        A deeper structure with multiple nested folders, no ignore.
        Just verify the structure is correct and the top name is the actual folder base by default.
        """
        self.create_file("a/b/c/d/file1.txt", "f1")
        self.create_file("a/b2/c2/file2.txt", "f2")
        self.create_file("z/y/x/last.txt", "last")

        data = self._run_prompt_generator()
        self.assertIn("structure", data)
        top_children = sorted(c["name"] for c in data["structure"]["children"])
        # We expect "a" and "z"
        self.assertEqual(top_children, ["a", "z"])

    def test_ignore_wildcard(self):
        """
        .gitignore: "*.log"
        Creates a.log, b.LOG => b.LOG is also ignored if no casefold,
        c.txt => keep
        """
        self.create_gitignore(".gitignore", "*.log\n")
        self.create_file("a.log", "should be ignored, no casefold needed, direct match")
        self.create_file("b.LOG", "not ignored if casefold=off, if we want ignore we must do casefold")
        self.create_file("c.txt", "keep me")

        data = self._run_prompt_generator()
        # "a.log" is ignored, "b.LOG" is not ignored (no casefold)
        top_children = sorted(c["name"] for c in data["structure"]["children"])
        # Expect ".gitignore", "b.LOG", "c.txt"
        self.assertEqual(top_children, [".gitignore", "b.LOG", "c.txt"])

    def test_ignore_wildcard_casefold(self):
        """
        Similar to above, but we pass --casefold => b.LOG is also ignored
        """
        self.create_gitignore(".gitignore", "*.log\n")
        self.create_file("a.log", "ignored direct")
        self.create_file("b.LOG", "ignored with casefold")
        self.create_file("c.txt", "kept")

        data = self._run_prompt_generator(extra_args=["--casefold"])
        top_children = sorted(c["name"] for c in data["structure"]["children"])
        # Now we only see ".gitignore", "c.txt"
        self.assertEqual(top_children, [".gitignore", "c.txt"])

    def test_special_chars(self):
        """
        Checks if files with special chars or unicode are displayed properly in structure.
        """
        self.create_file("résumé.doc", "RÉSUMÉ!")
        self.create_file("folder(1)/[project].txt", "some content")
        data = self._run_prompt_generator()
        # We expect ".gitignore" not present, we didn't create it.
        # top level: "folder(1)", "résumé.doc"
        top_children = sorted(c["name"] for c in data["structure"]["children"])
        self.assertEqual(top_children, ["folder(1)", "résumé.doc"])

        # inside folder(1) => one child "[project].txt"
        folder1 = next(c for c in data["structure"]["children"] if c["name"] == "folder(1)")
        self.assertEqual(len(folder1["children"]), 1)
        self.assertEqual(folder1["children"][0]["name"], "[project].txt")


if __name__ == "__main__":
    unittest.main()
