import unittest
import tempfile
import os
import json
import subprocess
import sys
import glob

# Directory where developers can drop test case JSON files.
TEST_CASES_DIR = "json_tests"  # Modify as needed.

class TestGitignoreCases(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_cases = []
        pattern = os.path.join(TEST_CASES_DIR, "t_*.json")
        for file_path in glob.glob(pattern):
            with open(file_path, "r") as f:
                try:
                    test_case = json.load(f)
                    # Optionally record the filename for error reporting.
                    test_case["_filename"] = os.path.basename(file_path)
                    cls.test_cases.append(test_case)
                except json.JSONDecodeError as e:
                    print(f"Error decoding {file_path}: {e}")

    def create_structure(self, node, base_path, gitignore_content=None):
        """
        Recursively create file/directory structure from a JSON node.
        Files are nodes without a "children" attribute.
        Directories have a "children" attribute (empty for empty directories).
        If the file is .gitignore, write the provided gitignore content.
        """
        name = node.get("name")
        children = node.get("children", None)
        target_path = os.path.join(base_path, name)
        
        if children is None:
            # Treat as a file.
            with open(target_path, "w") as f:
                if name == ".gitignore" and gitignore_content is not None:
                    f.write("\n".join(gitignore_content))
                else:
                    f.write("")
        else:
            if children:  # Non-empty directory.
                os.makedirs(target_path, exist_ok=True)
                for child in children:
                    self.create_structure(child, target_path, gitignore_content)
            else:
                # This is an empty directory (has "children": [] in the JSON).
                # If it's .gitignore, write its content.
                if name == ".gitignore":
                    with open(target_path, "w") as f:
                        if gitignore_content is not None:
                            f.write("\n".join(gitignore_content))
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
        self.create_structure(root_node, base_path, gitignore_content)
        return os.path.join(base_path, root_node["name"])
    
    def run_prompt_generator(self, directory):
        """
        Run the prompt_generator.py script on the given directory with -oj -s options.
        """
        cmd = [sys.executable, "prompt_generator.py", directory, "-oj", "-s"]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            self.fail(f"prompt_generator.py returned non-zero exit code.\nStderr: {result.stderr}")
        return result.stdout

    def normalize_tree(self, node):
        """
        Normalize a tree node to a tuple:
         - For directories (node has "children"): (name, sorted_list_of_normalized_children)
         - For files (node does not have "children"): (name, None)
        This normalization allows for order-insensitive comparisons.
        """
        name = node["name"]
        if "children" in node:
            norm_children = [self.normalize_tree(child) for child in node["children"]]
            norm_children.sort(key=lambda x: x[0])
            return (name, norm_children)
        else:
            return (name, None)

    def test_gitignore_cases(self):
        for idx, test_case in enumerate(self.test_cases):
            with self.subTest(test_case=test_case.get("_filename", f"Case {idx}")):
                gitignore_content = test_case.get("gitignore", [])
                initial_structure = test_case.get("initial_structure")
                expected_structure = test_case.get("tracked_structure")
                
                with tempfile.TemporaryDirectory() as tmpdir:
                    # Build the initial file structure in the temporary directory.
                    root_dir = self.build_structure(initial_structure, tmpdir, gitignore_content)
                    
                    # Run the prompt_generator script on the created directory.
                    output = self.run_prompt_generator(root_dir)
                    try:
                        output_json = json.loads(output)
                    except json.JSONDecodeError as e:
                        self.fail(f"Output is not valid JSON for {test_case.get('_filename') or f'Case {idx}'}:\n{output}\nError: {e}")
                    
                    # Extract the top-level "structure" nodes.
                    expected_tree = expected_structure.get("structure", expected_structure)
                    output_tree = output_json.get("structure", output_json)
                    
                    norm_expected = self.normalize_tree(expected_tree)
                    norm_output = self.normalize_tree(output_tree)
                    
                    self.assertEqual(
                        norm_output,
                        norm_expected,
                        f"Test case {test_case.get('_filename') or idx} failed.\nExpected (normalized): {norm_expected}\nGot (normalized): {norm_output}"
                    )

if __name__ == "__main__":
    unittest.main()
