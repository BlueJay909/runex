#!/usr/bin/env python
import unittest
from runex.wildmatch import wildmatch, WM_MATCH, WM_NOMATCH, WM_UNICODE

class PosixTest(unittest.TestCase):
    # For each POSIX class, we define (positive_examples, negative_examples)
    # For ASCII mode, only basic ASCII characters should match.
    POSIX_TEST_CASES_ASCII = {
        'alnum': (["a", "Z", "0", "9"], ["!", " "]),
        'alpha': (["a", "Z"], ["À", "文", "1", "!"]),  # Only a-z and A-Z should match.
        'ascii': (["a", "9", "!"], ["文", "€"]),
        'blank': ([" ", "\t"], ["\n", "a"]),
        'cntrl': (["\x00", "\x1F", "\x7F"], ["A", " "]),
        'digit': (["0", "5"], ["a", "!"]),
        'graph': (["!", "A", "~"], [" ", "\n"]),
        'lower': (["a", "z"], ["A", "0"]),
        'print': ([" ", "A", "9"], ["\x00", "\x1F"]),
        'punct': (["!", "?"], ["A", "1"]),
        'space': ([" ", "\t", "\n", "\r", "\v", "\f"], ["a", "1"]),
        'upper': (["A", "Z"], ["a", "0"]),
        'word':  (["a", "Z", "0", "_"], ["!", " "]),
        'xdigit': (["A", "f", "3"], ["g", "z"])
    }
    # For Unicode mode, extended letters are considered alpha.
    POSIX_TEST_CASES_UNICODE = {
        'alnum': (["a", "Z", "0", "9", "文"], ["!", " "]),
        'alpha': (["a", "Z", "À", "文", "ß"], ["1", "!"]),
        'ascii': (["a", "9", "!"], ["文", "€"]),
        'blank': ([" ", "\t"], ["\n", "a"]),
        'cntrl': (["\x00", "\x1F", "\x7F"], ["A", " "]),
        'digit': (["0", "5"], ["a", "!"]),
        'graph': (["!", "A", "~"], [" ", "\n"]),
        'lower': (["a", "z", "ß"], ["A", "0"]),
        'print': ([" ", "A", "9"], ["\x00", "\x1F"]),
        'punct': (["!", "?"], ["A", "1"]),
        'space': ([" ", "\t", "\n", "\r", "\v", "\f"], ["a", "1"]),
        'upper': (["A", "Z"], ["a", "0"]),
        'word':  (["a", "Z", "0", "_"], ["!", " "]),
        'xdigit': (["A", "f", "3"], ["g", "z"])
    }
    
    def run_test_for_class(self, cls_key, examples, flags):
        """
        Build the pattern "[[:cls_key:]]" and run wildmatch on each example.
        """
        pattern = f"[[:{cls_key}:]]"
        results = []
        for ex in examples:
            res = wildmatch(pattern, ex, flags)
            results.append((ex, res))
        return results

    def test_posix_ascii(self):
        """Test POSIX bracket expressions in ASCII mode (WM_UNICODE off)."""
        flags = 0  # No Unicode expansion.
        for cls, (positives, negatives) in self.POSIX_TEST_CASES_ASCII.items():
            with self.subTest(cls=cls, mode="ASCII"):
                pos_results = self.run_test_for_class(cls, positives, flags)
                neg_results = self.run_test_for_class(cls, negatives, flags)
                for ex, res in pos_results:
                    self.assertEqual(
                        res, WM_MATCH,
                        f"ASCII: Pattern [[:{cls}:]] should match positive example {ex!r}, got {res}"
                    )
                for ex, res in neg_results:
                    self.assertEqual(
                        res, WM_NOMATCH,
                        f"ASCII: Pattern [[:{cls}:]] should NOT match negative example {ex!r}, got {res}"
                    )
    
    def test_posix_unicode(self):
        """Test POSIX bracket expressions in Unicode mode (WM_UNICODE enabled)."""
        flags = WM_UNICODE
        for cls, (positives, negatives) in self.POSIX_TEST_CASES_UNICODE.items():
            with self.subTest(cls=cls, mode="Unicode"):
                pos_results = self.run_test_for_class(cls, positives, flags)
                neg_results = self.run_test_for_class(cls, negatives, flags)
                for ex, res in pos_results:
                    self.assertEqual(
                        res, WM_MATCH,
                        f"Unicode: Pattern [[:{cls}:]] should match positive example {ex!r}, got {res}"
                    )
                for ex, res in neg_results:
                    self.assertEqual(
                        res, WM_NOMATCH,
                        f"Unicode: Pattern [[:{cls}:]] should NOT match negative example {ex!r}, got {res}"
                    )

if __name__ == "__main__":
    unittest.main()
