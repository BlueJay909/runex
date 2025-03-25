#!/usr/bin/env python
import unittest
from codetext.wildmatch import wildmatch, WM_MATCH, WM_NOMATCH, WM_CASEFOLD, WM_PATHNAME, WM_UNICODE

class WildmatchTest(unittest.TestCase):
    def debug_test(self, pattern, text, flags):
        result = wildmatch(pattern, text, flags)
        print(f"DEBUG: wildmatch({pattern!r}, {text!r}, flags={flags}) -> {result}")
        return result

    def test_question_mark(self):
        self.assertEqual(wildmatch("a?c", "abc"), WM_MATCH)
        self.assertEqual(wildmatch("a?c", "ac"), WM_NOMATCH)

    def test_literal_match(self):
        # Basic literal match.
        self.assertEqual(self.debug_test("abc", "abc", 0), WM_MATCH)
        self.assertEqual(self.debug_test("abc", "ABC", 0), WM_NOMATCH)
        self.assertEqual(self.debug_test("abc", "ABC", WM_CASEFOLD), WM_MATCH)

    def test_star(self):
        # In Git's wildmatch, '*' matches any sequence of characters (except '/').
        self.assertEqual(self.debug_test("a*c", "abbbbbc", 0), WM_MATCH)
        self.assertEqual(self.debug_test("a*c", "ac", 0), WM_MATCH)
        # According to Git, "a*c" should match "abbdc" (because * matches "bbd")
        self.assertEqual(self.debug_test("a*c", "abbdc", 0), WM_MATCH)

    def test_posix_brackets(self):
        # Testing POSIX bracket expressions. Here we assume WM_UNICODE is on.
        self.assertEqual(self.debug_test("[[:digit:]]", "5", WM_UNICODE), WM_MATCH)
        self.assertEqual(self.debug_test("[[:alpha:]]", "a", WM_UNICODE), WM_MATCH)
        self.assertEqual(self.debug_test("[[:alpha:]]", "1", WM_UNICODE), WM_NOMATCH)
    
    def test_unicode_literals(self):
        # Test Unicode literal matching.
        self.assertEqual(self.debug_test("café", "café", 0), WM_MATCH)
        self.assertEqual(self.debug_test("café", "CAFÉ", 0), WM_NOMATCH)
        self.assertEqual(self.debug_test("café", "CAFÉ", WM_CASEFOLD), WM_MATCH)

if __name__ == "__main__":
    unittest.main()
