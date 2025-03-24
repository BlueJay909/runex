import unittest
import tempfile
import os
import json
import subprocess
import sys

class TestTrivialGitignore(unittest.TestCase):
    def setUp(self):
        # Test case: .gitignore contains a pattern to ignore "file.txt".
        self.test_case = {
            "gitignore": ["file.txt"],
            "initial_structure": {
                "structure": {
                    "name": "project",
                    "children": [
                        {"name": ".gitignore"},
                        {"name": "file.txt"}
                    ]
                }
            },
            "tracked_structure": {
                "structure": {
                    "name": "project",
                    "children": [
                        {"name": ".gitignore"}
                    ]
                }
            }
        }
    
    def create_structure(self, node, base_path, gitignore_content=None):
        name = node.get("name")
        # Use get("children") but if not present, then this is a file.
        children = node.get("children", None)
        target_path = os.path.join(base_path, name)
        
        if children is None:
            # Treat as a file.
            with open(target_path, "w") as f:
                # If this file is .gitignore, write the provided content.
                if name == ".gitignore" and gitignore_content is not None:
                    f.write("\n".join(gitignore_content))
                else:
                    f.write("")
        else:
            if children:  # Non-empty: create a directory and its children.
                os.makedirs(target_path, exist_ok=True)
                for child in children:
                    self.create_structure(child, target_path, gitignore_content)
            else:
                # Empty children: if the name is ".gitignore", write the content.
                if name == ".gitignore":
                    with open(target_path, "w") as f:
                        if gitignore_content is not None:
                            f.write("\n".join(gitignore_content))
                        else:
                            f.write("")
                elif '.' in name and name[0] != '.':
                    # Otherwise, if the name contains a dot, treat as file.
                    with open(target_path, "w") as f:
                        f.write("")
                else:
                    os.makedirs(target_path, exist_ok=True)
    
    def build_structure(self, structure_json, base_path, gitignore_content=None):
        root_node = structure_json["structure"]
        self.create_structure(root_node, base_path, gitignore_content)
        return os.path.join(base_path, root_node["name"])
    
    def run_prompt_generator(self, directory):
        # Run the prompt_generator.py script with -oj -s options.
        cmd = [sys.executable, "prompt_generator.py", directory, "-oj", "-s"]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            self.fail(f"prompt_generator.py returned non-zero exit code.\nStderr: {result.stderr}")
        return result.stdout

    def normalize_tree(self, node):
        """
        Normalize a node into a tuple: 
           (name, normalized_children)
        Files (without "children") are represented with children = None.
        Directories (with "children") are represented with a sorted list of normalized children.
        """
        name = node["name"]
        if "children" in node:
            norm_children = [self.normalize_tree(child) for child in node["children"]]
            norm_children.sort(key=lambda x: x[0])
            return (name, norm_children)
        else:
            return (name, None)

    def test_trivial_case(self):
        gitignore_content = self.test_case.get("gitignore", [])
        initial_structure = self.test_case.get("initial_structure")
        expected_structure = self.test_case.get("tracked_structure")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create the initial file structure.
            root_dir = self.build_structure(initial_structure, tmpdir, gitignore_content)
            # Run the prompt_generator script.
            output = self.run_prompt_generator(root_dir)
            try:
                output_json = json.loads(output)
            except json.JSONDecodeError as e:
                self.fail(f"Output is not valid JSON:\n{output}\nError: {e}")
            
            # Extract the top-level "structure" node.
            expected_tree = expected_structure.get("structure", expected_structure)
            output_tree = output_json.get("structure", output_json)
            
            norm_expected = self.normalize_tree(expected_tree)
            norm_output = self.normalize_tree(output_tree)
            
            self.assertEqual(
                norm_output,
                norm_expected,
                f"Trivial test failed.\nExpected (normalized): {norm_expected}\nGot (normalized): {norm_output}"
            )

if __name__ == "__main__":
    unittest.main()
