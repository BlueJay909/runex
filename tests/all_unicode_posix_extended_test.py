#!/usr/bin/env python
import unittest
import re
import unicodedata
from modules.wildmatch import (
    wildmatch, WM_MATCH, WM_NOMATCH, WM_UNICODE,
    POSIX_MAPPING, posix_alpha, posix_cntrl, posix_lower, posix_print,
    posix_punct, posix_upper
)

# For the classes we have custom Unicode–aware functions for in our module,
# we use them as the reference for supplementary samples.
# We define a dictionary of supplementary sample characters for a few keys.
# (These samples are chosen from supplementary blocks such as Mathematical Alphanumerics or emoji.)
SUPPLEMENTARY_SAMPLES = {
    # For alpha, we expect standard alphabetic characters.
    # U+1D400 (MATHEMATICAL BOLD CAPITAL A) and U+1D41A (MATHEMATICAL BOLD SMALL A)
    'alpha': ( [chr(0x1D400), chr(0x1D41A)], [chr(0x1F600)] ),  # U+1F600 (😀) is not alphabetic.
    # For digit, use a mathematical digit (U+1D7CE MATHEMATICAL BOLD DIGIT ZERO)
    'digit': ( [chr(0x1D7CE)], [chr(0x1F600)] ),
    # For lower, U+1D41A is lowercase; U+1D400 is uppercase.
    'lower': ( [chr(0x1D41A)], [chr(0x1D400), chr(0x1F600)] ),
    # For upper, U+1D400 is uppercase.
    'upper': ( [chr(0x1D400)], [chr(0x1D41A), chr(0x1F600)] ),
    # For alnum, combine alpha and digit.
    'alnum': ( [chr(0x1D400), chr(0x1D7CE)], [chr(0x1F600)] ),
    # For word, which is alnum or underscore.
    'word':  ( [chr(0x1D400), "0", "_"], [chr(0x1F600)] )
}

class SupplementaryPosixTest(unittest.TestCase):
    def test_supplementary_samples(self):
        """
        For selected POSIX bracket expressions, test a curated set of supplementary
        Unicode characters (outside the BMP) against wildmatch() with WM_UNICODE.
        
        For each class key, we provide a list of positive examples (which should match)
        and negative examples (which should not). The expected result is WM_MATCH for positives,
        and WM_NOMATCH for negatives.
        """
        for cls_key, (positives, negatives) in SUPPLEMENTARY_SAMPLES.items():
            pattern = f"[[:{cls_key}:]]"
            with self.subTest(posix_class=cls_key):
                for ch in positives:
                    result = wildmatch(pattern, ch, WM_UNICODE)
                    self.assertEqual(
                        result, WM_MATCH,
                        f"Supplementary: [[:{cls_key}:]] should match {ch!r} (U+{ord(ch):04X}), got {result}"
                    )
                for ch in negatives:
                    result = wildmatch(pattern, ch, WM_UNICODE)
                    self.assertEqual(
                        result, WM_NOMATCH,
                        f"Supplementary: [[:{cls_key}:]] should NOT match {ch!r} (U+{ord(ch):04X}), got {result}"
                    )

if __name__ == "__main__":
    unittest.main()
