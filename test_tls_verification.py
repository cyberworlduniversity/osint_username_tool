"""Regression tests for secure TLS defaults in username OSINT requests."""

import ast
import unittest
from pathlib import Path


class TLSVerificationTests(unittest.TestCase):
    def test_module_does_not_disable_tls_verification(self):
        source_path = Path(__file__).with_name("username_osint.py")
        tree = ast.parse(source_path.read_text(encoding="utf-8"))

        disabled_tls_calls = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            for keyword in node.keywords:
                if (
                    keyword.arg == "ssl"
                    and isinstance(keyword.value, ast.Constant)
                    and keyword.value.value is False
                ):
                    disabled_tls_calls.append(node.lineno)

        self.assertEqual(
            disabled_tls_calls,
            [],
            "TLS certificate verification must never be explicitly disabled.",
        )


if __name__ == "__main__":
    unittest.main()
