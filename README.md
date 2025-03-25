# Codetext

`codetext` is a python tool that generates a plain text or json representation of a project's directory structure (plus file contents) following Git's `.gitignore` path and file matching rules.

Without further ado let's share the motto of this project:

_Well_ <br>
_I guess that it's close enough until it isn't._

> [!NOTE]
> Before using this program it is highly recommended you read the [`Use of AI during development`](#use-of-ai-during-development) paragraph

## Purpose of This Program

_The og scope of the program_ was to cater the need of an easy and quick way (see rfc1925 point 7a) of providing "context" to a `large language model` service, without painstakingly crtl-c an ctrl-v(ing) source code out of the IDE into the browser, all while t(c)rying to explain to the llm where a file should be read from and what it should actually do. (you still have to paste it back so at least it's almost half of _the work_ done)

If you want that, we (me and gpt) have the [`codetext visual studio code extension`](#) available.

## Usage

`prompt_generator.py` `[-h]` `[--casefold]` `[--json]` `[--only-structure]` `[--relative-root]` `<root_dir>` `[output_file]`

```
positional arguments:
  root_dir              Root directory of the project to be scanned
  output_file           Optional output file (default: stdout)
```
```
options:
  -h, --help            show this help message and exit
  --casefold, -c        Enable case-insensitive matching (WM_CASEFOLD)
  --json, -oj           Output JSON instead of text
  --only-structure, -s  Omit file contents in the output
  --relative-root, -rr  Force the root directory name to be '.' insted of basename
```

In the default mode, after traversing the specified project directory, it builds and concatenates into a single file (or stdout):

1. A pretty-printed tree-style output of the folder structure (excluding ignored paths).
2. A concatenated listing of the file contents found along it's path (excluding ignored files).

The same output can be also requested in a `json` format and for _both_ you can request only the structure of the project to be returned.

## Examples

### tool executed with the --only-structure arg on the "." directory:

venvnicolobalestrino@Nicolos-Air codetext % `python prompt_generator.py . -s`

```
Project Structure:

codetext/
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
___

### tool executed with the --only-structure --json args on the "." directory:

venvnicolobalestrino@Nicolos-Air codetext % `python prompt_generator.py . -oj -s`
```
{
  "structure": {
    "name": "codetext",
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

The plain text output without the -s will output everything, following the `.gitignore` rules:

```
Project Structure:

...tree representation...

# File: README.md
# Path: README.md

# Codetext

`codetext` is a python tool that generates a plain text or json representation of a project's directory structure (plus file contents) following Git's `.gitignore` path and file matching rules.

Without further ado let's share the motto of this project:

_Well_ <br>
_I guess that it's close enough until it isn't._

etc etc etc etc
```

The json output will follow this standard:
- files will never have a children attribute
- directories, even if empty, will always have a children attribute

That's how you will be able to differentiate between them.

in `-s` mode the following will be omitted:
- "path" - full file path
- "content" - actual file source content

## Testing

Testing is so important, the initial tests i wrote with AI and are a pain to maintain, so there is a json test suite that will enable everyone to just submit actually humane tested test cases that then we can just run to make this implementation bulletproof, the tests are as follows:

ex, t_00.json

```
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

That's it, a json file:

- "gitignore": [] is an array containing strings that represent ignore rules, "gitignore": ["file.txt", "file2.csv"] ignores those two, "gitignore": ["!file.txt", "!file2.csv"] unignores them and so on.

- "initial_structure" will be used by the script to build using tempfile the actual directory structure, and, in the .gitignore if present, it will populate it with what was specified in step 1.

- "tracked_structure" is the expected behavior, if our script correctly mimics .gitignore rules, it should produce this output.

Please, write a lot of edge cases that make this program literally burn, this way it can become better.

At `tests/suite_test.py` there is the code that will run all of the .json test cases present in the `json_test_cases` folder

The other tests all pass for now, but a lot are duplicated and i'm not even sure what they do (AI generated), they are too many, and i'm lazy, so, you'll do the work if you want the tool!

## Use of AI during development

**Keep in mind**: this was written extensively with the use of AI llm models, in particular you can find code from OpenAI o3-mini-high, o3-mini - Deepseek R1 - Gemini 2.0 Flash

`o3-mini-high` overrall kept this project together,
when it got stuck i used `Deepseek R1` to get it-unstuck,
`Gemini 2.0 Flash`, well i played with it for a while but for now wasn't really helpful (it truly wasn't i can safely say now)

Code and Comments as well as knowledge on how git works come from the AI, and i just kind of directed the whole thing by approximation and intuition, in fact, the only thing that is not AI generated is this readme.

This code is not guaranteed to mimic 100% the behavior of the .gitignore ignore logic of the master and commander (c git) - it is the dream though, but, well, don't ask for the differences between .gitignore and this, because the AI doenn't know for now, and i certainly don't. I guess that it's close enough.


Hopefully it was useful!