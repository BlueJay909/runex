---
layout: default
title: Home
nav: true
---

# Welcome to Runex Documentation

Thank you for checking out our Runex project. If you've read our main README on GitHub, you already have a solid overview of what Runex does. This site dives deeper into the technical details and usage of Runex.

Runex generates a project prompt by scanning your project directory, applying Git's .gitignore rules, and outputting the result in either a plain text tree view or as a JSON structure. Here you'll find detailed guides on how each component works.

## Documentation Overview

- **[Home]({{ site.baseurl }}/README.html)**  
  The main README, compiled as HTML, gives you an introduction and overall view of the project.

- **[CLI Documentation]({{ site.baseurl }}/cli.html)**  
  Detailed usage examples and explanations for our command-line interface, including flag combinations and expected outputs.

- **[Core Module Documentation]({{ site.baseurl }}/core.html)**  
  An in-depth look at how Runex scans the project directory, filters files using .gitignore rules, and builds the final output.

- **[Ignore Logic Documentation]({{ site.baseurl }}/ignore_logic.html)**  
  A technical overview of how our tool processes .gitignore files and determines which files to ignore.

- **[Wildmatch Documentation]({{ site.baseurl }}/wildmatch.html)**  
  A detailed explanation of our wildcard matching implementation, including how flags like WM_CASEFOLD, WM_PATHNAME, and WM_UNICODE affect matching.

## How to Use This Documentation

This site is built using Jekyll and is automatically updated via GitHub Actions. The documentation is split between the content from the repository root (the compiled README) and additional markdown files in the `docs/` folder.

- Navigate using the menu links above to dive into each section.
- For a quick project overview, start with the **Home (Compiled README)** page.
- To learn how to run Runex, check out the **CLI Documentation**.
- Developers looking for technical details should read the **Core**, **Ignore Logic**, and **Wildmatch** documents.

---

We appreciate your interest in Runex and hope this documentation helps you integrate, extend, or contribute to the project. Happy coding!
