"""Regression checks for the M3G AGP runtime/classloader contract."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]


class M3GGradleKtsSyntax(unittest.TestCase):
    def test_gradle_scripts_use_kotlin_comments(self):
        for relative in ("buildSrc/build.gradle.kts", "build.gradle.kts", "app/build.gradle.kts"):
            with self.subTest(file=relative):
                source = (ROOT / relative).read_text(encoding="utf-8")
                self.assertNotRegex(
                    source, r"(?m)^\s*#",
                    "Kotlin DSL does not accept shell-style # comments"
                )
        source = (ROOT / "buildSrc/build.gradle.kts").read_text(encoding="utf-8")
        self.assertIn("// M3G visitor needs AGP at both compile time and runtime.", source)

    def test_agp_available_at_runtime_without_versioned_plugin_conflict(self):
        buildsrc = (ROOT / "buildSrc/build.gradle.kts").read_text(encoding="utf-8")
        root = (ROOT / "build.gradle.kts").read_text(encoding="utf-8")
        app = (ROOT / "app/build.gradle.kts").read_text(encoding="utf-8")
        self.assertIn('implementation("com.android.tools.build:gradle:8.10.1")', buildsrc)
        self.assertNotIn('compileOnly("com.android.tools.build:gradle:8.10.1")', buildsrc)
        self.assertIn('id("com.android.application") apply false', root)
        self.assertIn('id("com.android.application")', app)
        self.assertNotIn('alias(libs.plugins.android.application)', root)
        self.assertNotIn('alias(libs.plugins.android.application)', app)
        self.assertIn('AndroidSafeMachineIdVisitorFactory::class.java', app)
        self.assertIn('InstrumentationScope.ALL', app)


if __name__ == "__main__":
    unittest.main()
