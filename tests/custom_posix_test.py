#!/usr/bin/env python
import unittest
from runex.wildmatch import posix_alpha, posix_cntrl, posix_lower, posix_print, posix_punct, posix_upper

class CustomPosixTest(unittest.TestCase):
    def test_posix_alpha(self):
        # Letters should return True.
        self.assertTrue(posix_alpha("a"))
        self.assertTrue(posix_alpha("Z"))
        self.assertTrue(posix_alpha("ß"))  # Python considers ß as alphabetic.
        self.assertTrue(posix_alpha("文"))
        # Non-letters should return False.
        self.assertFalse(posix_alpha("1"))
        self.assertFalse(posix_alpha("!"))
        self.assertFalse(posix_alpha(" "))

    def test_posix_cntrl(self):
        # Control characters (category "Cc") should return True.
        self.assertTrue(posix_cntrl("\x00"))
        self.assertTrue(posix_cntrl("\x1F"))
        self.assertTrue(posix_cntrl("\x7F"))
        # Non-control characters.
        self.assertFalse(posix_cntrl("A"))
        self.assertFalse(posix_cntrl(" "))

    def test_posix_lower(self):
        # Lowercase letters should return True.
        self.assertTrue(posix_lower("a"))
        self.assertTrue(posix_lower("z"))
        self.assertTrue(posix_lower("ß"))  # ß is lowercase in Python.
        # Uppercase letters or non-letters.
        self.assertFalse(posix_lower("A"))
        self.assertFalse(posix_lower("1"))
        self.assertFalse(posix_lower("!"))

    def test_posix_print(self):
        # Printable characters should return True.
        self.assertTrue(posix_print("A"))
        self.assertTrue(posix_print(" "))
        self.assertTrue(posix_print("é"))
        self.assertTrue(posix_print("文"))
        # Control characters are not printable.
        self.assertFalse(posix_print("\x00"))
        self.assertFalse(posix_print("\x1F"))
        self.assertFalse(posix_print("\n"))  # Depending on interpretation, newline might be considered non-printable.

    def test_posix_punct(self):
        # Punctuation: any character with Unicode category starting with "P".
        self.assertTrue(posix_punct("!"))
        self.assertTrue(posix_punct("?"))
        self.assertTrue(posix_punct(","))
        # Letters or digits are not punctuation.
        self.assertFalse(posix_punct("A"))
        self.assertFalse(posix_punct("1"))
        self.assertFalse(posix_punct("文"))

    def test_posix_upper(self):
        # Uppercase letters should return True.
        self.assertTrue(posix_upper("A"))
        self.assertTrue(posix_upper("Z"))
        # Lowercase letters or non-letters should return False.
        self.assertFalse(posix_upper("a"))
        self.assertFalse(posix_upper("ß"))
        self.assertFalse(posix_upper("1"))
        self.assertFalse(posix_upper("!"))

if __name__ == "__main__":
    unittest.main()
