"""Regression for the M3G buildSrc Kotlin Gradle DSL syntax failure."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]


class M3GGradleKtsSyntax(unittest.TestCase):
    def test_buildsrc_has_valid_kotlin_comments(self):
        source = (ROOT / "buildSrc/build.gradle.kts").read_text(encoding="utf-8")
        self.assertIn("// AGP API is needed to compile the visitor", source)
        self.assertNotRegex(source, r"(?m)^\s*#", "Kotlin DSL does not allow shell-style # comments")

    def test_agp_api_is_compile_only(self):
        source = (ROOT / "buildSrc/build.gradle.kts").read_text(encoding="utf-8")
        self.assertIn('compileOnly("com.android.tools.build:gradle:8.10.1")', source)
        self.assertNotIn('implementation("com.android.tools.build:gradle:8.10.1")', source)


if __name__ == "__main__":
    unittest.main()
