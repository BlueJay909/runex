import unittest
import tempfile
import os
import json
import subprocess
import sys
import glob
import difflib

# Directory where test case JSON files are stored.
TEST_CASES_DIR = "json_test_cases"  # Modify as needed.

class TestGitignoreCases(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_cases = []
        pattern = os.path.join(TEST_CASES_DIR, "t_*.json")
        for file_path in glob.glob(pattern):
            with open(file_path, "r") as f:
                try:
                    test_case = json.load(f)
                    test_case["_filename"] = os.path.basename(file_path)
                    cls.test_cases.append(test_case)
                except json.JSONDecodeError as e:
                    print(f"Error decoding {file_path}: {e}")

    def create_structure(self, node, base_path, global_gitignore_content=None, level=0):
        """
        Recursively create file/directory structure from a JSON node.
        - Files (nodes without a "children" key) are created as files.
        - Directories (nodes with a "children" key) are created as directories.
        
        For a node named ".gitignore":
          - If the node has a "contents" field, write that.
          - Else, if it is at level 1 (a direct child of the project root) and
            global_gitignore_content is provided, write that.
          - Otherwise, create an empty file.
        """
        name = node.get("name")
        children = node.get("children", None)
        target_path = os.path.join(base_path, name)
        
        if children is None:
            # Treat as a file.
            with open(target_path, "w") as f:
                if name == ".gitignore":
                    if "contents" in node:
                        f.write("\n".join(node["contents"]))
                    elif level == 1 and global_gitignore_content is not None:
                        f.write("\n".join(global_gitignore_content))
                    else:
                        f.write("")
                else:
                    f.write("")
        else:
            if children:
                os.makedirs(target_path, exist_ok=True)
                for child in children:
                    self.create_structure(child, target_path, global_gitignore_content, level=level+1)
            else:
                # Empty directory.
                if name == ".gitignore":
                    with open(target_path, "w") as f:
                        if "contents" in node:
                            f.write("\n".join(node["contents"]))
                        elif level == 1 and global_gitignore_content is not None:
                            f.write("\n".join(global_gitignore_content))
                        else:
                            f.write("")
                else:
                    os.makedirs(target_path, exist_ok=True)

    def build_structure(self, structure_json, base_path, gitignore_content=None):
        """
        Create the full structure starting from the top-level "structure" key.
        Returns the path to the root directory.
        """
        root_node = structure_json["structure"]
        # Call create_structure with level 0 for the root.
        self.create_structure(root_node, base_path, gitignore_content, level=0)
        return os.path.join(base_path, root_node["name"])
    
    def run_prompt_generator(self, directory):
        """
        Run prompt_generator.py on the given directory with -oj -s options.
        """
        cmd = [sys.executable, "prompt_generator.py", directory, "-oj", "-s"]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            self.fail(f"prompt_generator.py returned non-zero exit code.\nStderr: {result.stderr}")
        return result.stdout

    def normalize_tree(self, node):
        """
        Normalize a tree node to a tuple:
          - For directories (node has "children"): (name, sorted list of normalized children)
          - For files (node does not have "children"): (name, None)
        This allows order-insensitive comparison.
        """
        name = node["name"]
        if "children" in node:
            norm_children = [self.normalize_tree(child) for child in node["children"]]
            norm_children.sort(key=lambda x: x[0])
            return (name, norm_children)
        else:
            return (name, None)

    def get_diff(self, expected, output):
        """
        Generate a unified diff between expected and output JSON strings.
        """
        expected_str = json.dumps(expected, indent=2, sort_keys=True)
        output_str = json.dumps(output, indent=2, sort_keys=True)
        diff_lines = list(difflib.unified_diff(
            expected_str.splitlines(),
            output_str.splitlines(),
            fromfile="expected",
            tofile="output",
            lineterm=""
        ))
        return "\n".join(diff_lines)

    def test_gitignore_cases(self):
        for idx, test_case in enumerate(self.test_cases):
            with self.subTest(test_case=test_case.get("_filename", f"Case {idx}")):
                gitignore_content = test_case.get("gitignore", [])
                initial_structure = test_case.get("initial_structure")
                expected_structure = test_case.get("tracked_structure")
                
                with tempfile.TemporaryDirectory() as tmpdir:
                    # Build the initial file structure.
                    root_dir = self.build_structure(initial_structure, tmpdir, gitignore_content)
                    # Run the prompt_generator script.
                    output = self.run_prompt_generator(root_dir)
                    try:
                        output_json = json.loads(output)
                    except json.JSONDecodeError as e:
                        self.fail(f"Output is not valid JSON for {test_case.get('_filename') or f'Case {idx}'}:\n{output}\nError: {e}")
                    
                    # Extract top-level "structure" nodes.
                    expected_tree = expected_structure.get("structure", expected_structure)
                    output_tree = output_json.get("structure", output_json)
                    
                    norm_expected = self.normalize_tree(expected_tree)
                    norm_output = self.normalize_tree(output_tree)
                    
                    try:
                        self.assertEqual(norm_output, norm_expected)
                    except AssertionError:
                        diff = self.get_diff(norm_expected, norm_output)
                        self.fail(f"Test case {test_case.get('_filename') or idx} failed.\nDiff:\n{diff}")

if __name__ == "__main__":
    unittest.main()
