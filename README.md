# Runex
> A context generation tool to bring vibe coding in your life... or do even more.

---

## Introduction

`runex` is a python tool that generates a `plain-text` or `json` representation of a **project's directory structure** (_plus file contents_), following Git's own `.gitignore` path and file matching rules.

> _Everything's close enough... `until it isn't.`_

> [!NOTE]  
> Before using this program it is highly recommended you read the [`Use of AI during development`](#use-of-ai-during-development) paragraph

---

## Example output(s)

_Let's see if this can be good for you, will it be love at first sight?_

### Default behavior

#### `plain-text`
> no args needed

**You ask:**
```bash
python prompt_generator.py .
```

**You get:**
```plaintext
Project Structure:

my-project/
├── .gitignore
├── src/
│   └── next-big-thing.py
└── tests/


# File: next-big-thing.py
# Path: src/next-big-thing.py

#!/usr/bin/env python
"""
Hey there
"""
    
if __name__ == "__main__":
    print("Hello World!")
```

#### `json`
> add `-oj`

**You ask:**
```bash
python prompt_generator.py . -oj
```

**You get:**
```json
{
  "structure": {
    "name": "my-project",
    "children": [
      {
        "name": ".gitignore"
      },
      {
        "name": "src",
        "children": [
          {
            "name": "next-big-thing.py"
          }
        ]
      },
      {
        "name": "tests",
        "children": []
      }
    ]
  },
  "files": [
    {
      "filename": "next-big-thing.py",
      "path": "src/next-big-thing.py",
      "content": "#!/usr/bin/env python\n\"\"\"\nHey there\n\"\"\"\n    \nif __name__ == \"__main__\":\n    print(\"Hello World!\")\n"
    }
  ]
}
```

---

### No need for file contents?
> just add `-s`

#### `plain text`

**You ask:**
```bash
python prompt_generator.py . -s
```

**You get:**
```plaintext
Project Structure:

my-project/
├── .gitignore
├── src/
│   └── next-big-thing.py
└── tests/
```

#### `json`

**You ask:**
```bash
python prompt_generator.py . -oj -s
```

**You get:**
```json
{
  "structure": {
    "name": "my-project",
    "children": [
      {
        "name": ".gitignore"
      },
      {
        "name": "src",
        "children": [
          {
            "name": "next-big-thing.py"
          }
        ]
      },
      {
        "name": "tests",
        "children": []
      }
    ]
  }
}
```

---

So, you got this far.

You _might_ need this tool? <br>
Well...

<details>
  <summary>What have we learned other than that?</summary>
  
  > Answer:  
  _You ask, You get_ <br>
</details>

---

## Purpose of This Program

The _og_ scope of _the program_ was to cater the need for an easy and quick way ([see rfc1925 point 7a](https://www.rfc-editor.org/rfc/rfc1925.txt)) of providing "context" to a `large language model` service, without _painstakingly_ crtl-c an ctrl-v(ing) source code out of the IDE into the browser, all while t(c)rying to explain to the llm where a file should be read from and what it should actually do. (you still have to paste it back to the IDE so at least it's almost half of _the work_ done)

If you want that, _we_ (me and gpt) have a [`runex visual studio code extension`](#) available.

---

## Usage - Deep Dive

```
prompt_generator.py [-h] [--casefold] [--json] [--only-structure] [--relative-root] <root_dir> [output_file]
```

### Positional arguments:
- **root_dir**  
  Root directory of the project to be scanned
- **output_file**  
  Optional output file (default: stdout)

### Options:
- `-h, --help`  
  show this help message and exit
- `--casefold, -c`  
  Enable case-insensitive matching (WM_CASEFOLD)
- `--json, -oj`  
  Output JSON instead of text
- `--only-structure, -s`  
  Omit file contents in the output
- `--relative-root, -rr`  
  Force the root directory name to be '.' instead of basename

In the default mode, after traversing the specified project directory, `runex` builds and concatenates into a single file (or stdout):

1. A pretty-printed tree-style output of the folder structure (excluding ignored paths).
2. A concatenated listing of the file contents found along it's path (excluding ignored files).

The same output can be also requested in a `json` format and for both you can request only the structure of the project to be returned.

---

## Examples

### Tool executed with the `--only-structure` arg on the "." directory:

```bash
venvnicolobalestrino@Nicolos-Air runex % python prompt_generator.py . -s
```

```plaintext
Project Structure:

runex/
├── .gitignore
├── README.md
├── json_test_cases/
│   ├── t_00.json
│   ├── t_01.json
│   ├── t_02.json
│   ├── t_03.json
│   ├── t_04.json
│   ├── t_05.json
│   ├── t_06.json
│   ├── t_07.json
│   ├── t_08.json
│   ├── t_09.json
│   ├── t_10.json
│   ├── t_11.json
│   └── t_12.json
├── modules/
│   ├── __init__.py
│   ├── ignore_logic.py
│   └── wildmatch.py
├── prompt_generator.py
├── requirements.txt
└── tests/
    ├── __init__.py
    ├── all_unicode_posix_extended_test.py
    ├── all_unicode_posix_test.py
    ├── custom_posix_test.py
    ├── deepseek_test.py
    ├── extreme_test.py
    ├── gitignore_doc_json_test.py
    ├── ignore_logic_test.py
    ├── posix_test.py
    ├── prompt_generation_test.py
    ├── prompt_generator_json_test.py
    ├── suite_test.py
    ├── te_test.py
    └── wildmatch_test.py
```

---

### Tool executed with the `--only-structure` and `--json` args on the "." directory:

```bash
venvnicolobalestrino@Nicolos-Air runex % python prompt_generator.py . -oj -s
```

```json
{
  "structure": {
    "name": "runex",
    "children": [
      {
        "name": ".gitignore"
      },
      {
        "name": "README.md"
      },
      {
        "name": "json_test_cases",
        "children": [
          {
            "name": "t_00.json"
          },
          {
            "name": "t_01.json"
          },
          {
            "name": "t_02.json"
          },
          {
            "name": "t_03.json"
          },
          {
            "name": "t_04.json"
          },
          {
            "name": "t_05.json"
          },
          {
            "name": "t_06.json"
          },
          {
            "name": "t_07.json"
          },
          {
            "name": "t_08.json"
          },
          {
            "name": "t_09.json"
          },
          {
            "name": "t_10.json"
          },
          {
            "name": "t_11.json"
          },
          {
            "name": "t_12.json"
          }
        ]
      },
      {
        "name": "modules",
        "children": [
          {
            "name": "__init__.py"
          },
          {
            "name": "ignore_logic.py"
          },
          {
            "name": "wildmatch.py"
          }
        ]
      },
      {
        "name": "prompt_generator.py"
      },
      {
        "name": "requirements.txt"
      },
      {
        "name": "tests",
        "children": [
          {
            "name": "__init__.py"
          },
          {
            "name": "all_unicode_posix_extended_test.py"
          },
          {
            "name": "all_unicode_posix_test.py"
          },
          {
            "name": "custom_posix_test.py"
          },
          {
            "name": "deepseek_test.py"
          },
          {
            "name": "extreme_test.py"
          },
          {
            "name": "gitignore_doc_json_test.py"
          },
          {
            "name": "ignore_logic_test.py"
          },
          {
            "name": "posix_test.py"
          },
          {
            "name": "prompt_generation_test.py"
          },
          {
            "name": "prompt_generator_json_test.py"
          },
          {
            "name": "suite_test.py"
          },
          {
            "name": "te_test.py"
          },
          {
            "name": "wildmatch_test.py"
          }
        ]
      }
    ]
  }
}
```

The `plain text` output without the `-s` will output everything, following the `.gitignore` rules:

```plaintext
Project Structure:

...tree representation...

# File: README.md
# Path: README.md

# Runex

`runex` is a python tool that generates a plain text or json representation of a project's directory structure (plus file contents) following Git's `.gitignore` path and file matching rules.

Without further ado let's share the motto of this project:

_Well_ <br>
_I guess that it's close enough until it isn't._

etc etc etc etc
```

The `json` output will follow this standard:
- files will never have a children attribute  
- directories, even if empty, will always have a children attribute

That's how you will be able to differentiate between them.

In `-s` mode the following will be omitted:
- "path" - full file path  
- "content" - actual file source content

---

## Testing

The goal of this program is to mimic 100% the `.gitignore` logic, so we need a way of testing that.

The initial tests during development were written with AI in an unreliable way (you will find them under the `tests` directory) and were a pain to maintain.

So now, there is a single test file that actually matters, it is: `tests/suite_test.py`

This, will read and execute against `runex`'s json output, multiple test cases, written and evaluated by a human, found in a specific dedicated folder `json_test_cases` all following the naming `t_*.json`.

This will enable **you** to just submit truly tested cases to which the expected git behavior is known, this way we can just make this implementation bulletproof.

The test format goes as follows:

#### ex, t_00.json
```json
{
    "gitignore": [],
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
                {"name": ".gitignore"},
                {"name": "file.txt"}
            ]
        }
    }
}
```

That's it, a `json` file:

- `"gitignore": []` is an array containing strings that represent ignore rules, `"gitignore": ["file.txt", "file2.csv"]` ignores those two files, `"gitignore": ["!file.txt", "!file2.csv"]` unignores them and so on, see each element of the array as being one line of a `.gitignore`.

- `"initial_structure"` will be used by the script to build, using `tempfile`, the actual directory and file structure to test against  
    - the `.gitignore`, if present in the `initial_structure`, will be populated with the contents found in the array of _step 1_.

- `"tracked_structure"` is the expected behavior, if our script correctly mimics `.gitignore` rules, it will produce this output.

If the output produced by `runex` when run against `initial_structure` matches 100% the `tracked_structure` the single test case will be passed.

### What about nested `.gitignore files`?

This is how you can do it:
```json
{
    "gitignore": ["file.txt"],
    "initial_structure": {
        "structure": {
            "name": "project",
            "children": [
                {
                    "name": ".gitignore",
                    "contents": ["!file.txt"]
                },
                {"name": "file.txt"}
            ]
        }
    },
    "tracked_structure": {
        "structure": {
            "name": "project",
            "children": [
                {"name": ".gitignore"},
                {"name": "file.txt"}
            ]
        }
    }
}
```

In the `initial_structure` if you create a child named `.gitignore` and you give it a `contents` key whose value is an array structured just like the array in the simple test cases described before, upon folder creation that file will be written with the specified contents.  
If no contents are provided the program will just leave it empty.

Please, write a lot of edge cases that will make this program **_literally burn_**, this is the only way it will become better.

I mean everything, posix bracket expressions, unicode characters, nested structures combined and coordinated firework explosions etcetera.

At `tests/suite_test.py` there is the code that will run all of the `t_*.json` test cases present in the `json_test_cases` folder.

The other tests found under `tests` all pass for now, so in theory the program should be kept so that they keep passing in the future, but given that they were all AI generated... they might just be wrong, a lot of them are duplicated, and i'm not even sure what all of them actually do, they are too many, and i'm too lazy, so, **_you'll do the work if you want the tool!_**

The main intended way of testing this program from now on is adding tests under the folder `json_test_cases`

---

## Use of AI during development

**Keep in mind**: this was written extensively with the use of AI llm models, in particular you can find code from OpenAI o3-mini-high, o3-mini - Deepseek R1 - Gemini 2.0 Flash

`o3-mini-high` overrall kept this project together,  
when it got stuck i used `Deepseek R1` to get it-unstuck,  
`Gemini 2.0 Flash`, well i played with it for a while but for now wasn't really helpful (it truly wasn't i can safely say now)

Code and Comments as well as knowledge on how git works come from the AI, and i just kind of directed the whole thing by approximation and intuition, in fact, the only thing that is not AI generated is this readme.

This code is not guaranteed to mimic 100% the behavior of the `.gitignore` ignore logic of the master and commander (c git) - it is the dream though, but, well, don't ask for the differences between .gitignore and this, because the AI doenn't know for now, and i certainly don't. I guess that it's close enough.

---

Hopefully it was useful!
