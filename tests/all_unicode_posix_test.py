#!/usr/bin/env python
import unittest
import re
from codetext.wildmatch import (
    wildmatch, WM_MATCH, WM_NOMATCH, WM_UNICODE, 
    POSIX_MAPPING, posix_alpha, posix_cntrl, posix_lower, posix_print,
    posix_punct, posix_upper
)

# Build a dictionary for custom functions provided in the module.
CUSTOM_FUNCS = {
    'alpha': posix_alpha,
    'cntrl': posix_cntrl,
    'lower': posix_lower,
    'print': posix_print,
    'punct': posix_punct,
    'upper': posix_upper
}

class AllUnicodePosixTest(unittest.TestCase):
    def test_all_unicode_posix(self):
        """
        For each POSIX bracket expression (e.g. [[:alpha:]]),
        iterate over all Unicode BMP code points (0x0000-0xFFFF, skipping surrogates)
        and assert that wildmatch(pattern, ch, WM_UNICODE) returns WM_MATCH
        if and only if the corresponding reference function (custom if available, 
        otherwise a regex built from the mapping's Unicode expansion) indicates a match.
        """
        for cls_key, mapping in POSIX_MAPPING.items():
            pattern = f"[[:{cls_key}:]]"
            # Determine the reference mechanism: custom function if available, else regex.
            if cls_key in CUSTOM_FUNCS:
                ref_func = CUSTOM_FUNCS[cls_key]
            else:
                # Use Unicode expansion if provided; otherwise fallback to ASCII expansion.
                exp = mapping[1] if mapping[1] is not None else mapping[0]
                # Build a regex that matches a single character in the class.
                try:
                    ref_regex = re.compile(f"^[{exp}]$")
                except re.error:
                    # If regex fails to compile, skip this class.
                    continue
                def ref_func(ch, regex=ref_regex):
                    return regex.fullmatch(ch) is not None

            with self.subTest(posix_class=cls_key):
                for codepoint in range(0x0000, 0x10000):
                    # Skip surrogate range.
                    if 0xD800 <= codepoint <= 0xDFFF:
                        continue
                    ch = chr(codepoint)
                    expected = WM_MATCH if ref_func(ch) else WM_NOMATCH
                    result = wildmatch(pattern, ch, WM_UNICODE)
                    self.assertEqual(
                        result, expected,
                        f"POSIX [[:{cls_key}:]] on U+{codepoint:04X} ({ch!r}): expected {expected}, got {result}"
                    )

if __name__ == "__main__":
    unittest.main()
