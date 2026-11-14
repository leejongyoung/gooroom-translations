"""Build driver tests with a fake msgfmt, not a full Debian package build."""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

BUILD_SCRIPT = Path(__file__).resolve().parents[1] / "build.sh"


class BuildFailureTests(unittest.TestCase):
    def run_build(self, failing_catalog=""):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            shutil.copy2(BUILD_SCRIPT, root / "build.sh")
            commands = root / "bin"
            commands.mkdir()
            msgfmt = commands / "msgfmt"
            msgfmt.write_text(
                "#!/bin/sh\n"
                'if [ -n "$FAIL_CATALOG" ]; then\n'
                '  case "$*" in *"$FAIL_CATALOG"*) echo "injected msgfmt failure" >&2; exit 42;; esac\n'
                "fi\n"
                "exit 0\n"
            )
            msgfmt.chmod(0o755)
            environment = {
                **os.environ,
                "PATH": str(commands)
                + os.pathsep
                + os.environ.get("PATH", "/usr/bin:/bin"),
                "FAIL_CATALOG": failing_catalog,
            }
            return subprocess.run(
                ["bash", "build.sh"],
                cwd=root,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )

    @unittest.skipUnless(shutil.which("msgfmt"), "gettext msgfmt is not installed")
    def test_synaptic_catalog_compiles_with_real_gettext(self):
        catalog = BUILD_SCRIPT.parent / "po/synaptic/synaptic-ko.po"
        with tempfile.TemporaryDirectory() as temporary:
            result = subprocess.run(
                [
                    "msgfmt",
                    "-c",
                    str(catalog),
                    "-o",
                    str(Path(temporary) / "synaptic.mo"),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_middle_catalog_failure_propagates(self):
        result = self.run_build("gnome-panel-ko.po")
        self.assertIn("injected msgfmt failure", result.stderr)
        self.assertNotEqual(result.returncode, 0)

    def test_last_catalog_failure_propagates(self):
        result = self.run_build("malcontent-ko.po")
        self.assertIn("injected msgfmt failure", result.stderr)
        self.assertNotEqual(result.returncode, 0)

    def test_all_catalogs_success_returns_zero(self):
        result = self.run_build()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_first_catalog_failure_propagates(self):
        result = self.run_build("gooroom-update-ko.po")
        self.assertIn("injected msgfmt failure", result.stderr)
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
