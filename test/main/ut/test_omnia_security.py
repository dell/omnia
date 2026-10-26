# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Unit tests for the omnia.sh security hardening and the test command builder.

Covers env-file trust validation and PATH hijack resistance
(validate_env_source), safe recursive deletion (safe_rm_dir), and shell quoting
of command templates (build_cmd).
"""

import os
from pathlib import Path
import shutil
import string
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = Path(__file__).resolve().parents[3]
OMNIA_SH = REPO_ROOT / "src" / "main" / "omnia.sh"
sys.path.insert(0, str(REPO_ROOT / "test" / "main"))

# pylint: disable-next=wrong-import-position
from library.vars.common_vars import CMDS, build_cmd


def make_temp_dir(test_case):
    """Create a temporary directory that is removed when the test finishes."""
    path = tempfile.mkdtemp()
    test_case.addCleanup(shutil.rmtree, path, ignore_errors=True)
    return path


def run_omnia_function(call, extra_env=None):
    """Source omnia.sh and run one shell call, returning the completed process."""
    env = dict(os.environ)
    env.update(extra_env or {})
    return subprocess.run(
        ["/usr/bin/bash", "-c", f'source "{OMNIA_SH}"; {call}'],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )


class ValidateEnvSourceTest(unittest.TestCase):
    """validate_env_source: file trust checks and PATH hijack resistance."""

    def setUp(self):
        self.dir = Path(make_temp_dir(self))
        self.env_file = self.dir / "omnia.env"
        self.env_file.write_text("SYSTEM_ADMIN_NIC_IPV4=10.1.2.3\n")
        self.env_file.chmod(0o644)

    def validate(self, path):
        """Run validate_env_source against the given path."""
        return run_omnia_function(f'validate_env_source "{path}"')

    def test_valid_env_file_passes(self):
        """A root/user-owned, non-writable file with a valid IP is accepted."""
        result = self.validate(self.env_file)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_symlinked_env_file_is_rejected(self):
        """A symbolic link is refused before it is sourced."""
        link = self.dir / "link.env"
        link.symlink_to(self.env_file)
        result = self.validate(link)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("no symbolic links", result.stdout)

    def test_group_writable_env_file_is_rejected(self):
        """A group-writable file is refused."""
        self.env_file.chmod(0o664)
        result = self.validate(self.env_file)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("group- or world-writable", result.stdout)

    def test_world_writable_env_file_is_rejected(self):
        """A world-writable file is refused."""
        self.env_file.chmod(0o646)
        result = self.validate(self.env_file)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("group- or world-writable", result.stdout)

    @unittest.skipUnless(os.geteuid() == 0, "chown requires root")
    def test_env_file_owned_by_other_user_is_rejected(self):
        """A file owned by neither root nor the invoking user is refused."""
        os.chown(self.env_file, 12345, 12345)
        result = self.validate(self.env_file)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("owned by root or the invoking user", result.stdout)

    def test_trojan_bash_and_env_in_caller_path_are_not_executed(self):
        """Binaries planted first in the caller's PATH are never run."""
        marker = self.dir / "hijacked"
        evil_dir = self.dir / "evil"
        evil_dir.mkdir()
        for name in ("bash", "env"):
            trojan = evil_dir / name
            trojan.write_text(f"#!/bin/sh\ntouch '{marker}'\nexit 0\n")
            trojan.chmod(0o755)

        # Poison PATH only after omnia.sh is sourced, so the hostile directory
        # is visible to validate_env_source but not to the test harness itself.
        result = run_omnia_function(
            f'PATH="{evil_dir}:$PATH"; validate_env_source "{self.env_file}"'
        )

        self.assertFalse(marker.exists(), "trojan binary from PATH was executed")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class SafeRmDirTest(unittest.TestCase):
    """safe_rm_dir: refuses unsafe targets and removes legitimate ones."""

    def setUp(self):
        self.dir = Path(make_temp_dir(self))

    def safe_rm(self, path):
        """Run safe_rm_dir with the data path anchored to the temp directory."""
        return run_omnia_function(
            f'safe_rm_dir "{path}"',
            {
                "OMNIA_DATA_PATH": str(self.dir),
                "OMNIA_VENV_PATH": str(self.dir / "venv"),
            },
        )

    def test_regular_directory_is_removed(self):
        """A normal directory under the data path is deleted."""
        target = self.dir / "venv"
        (target / "bin").mkdir(parents=True)
        (target / "bin" / "python").write_text("x")
        result = self.safe_rm(target)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(target.exists())

    def test_empty_path_is_refused(self):
        """An empty path is refused."""
        result = self.safe_rm("")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("empty path", result.stderr)

    def test_symlink_is_refused_and_target_preserved(self):
        """A symlink is refused and its target is left untouched."""
        real = self.dir / "real"
        real.mkdir()
        (real / "keep").write_text("x")
        link = self.dir / "venv_link"
        link.symlink_to(real)
        result = self.safe_rm(link)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("symbolic link", result.stderr)
        self.assertTrue((real / "keep").exists())
        self.assertTrue(link.is_symlink())

    def test_system_directories_are_refused(self):
        """System directories are never removed."""
        for path in ("/", "/usr", "/etc", "/opt", "/var", "/root", "/tmp"):
            with self.subTest(path=path):
                result = self.safe_rm(path)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("unsafe system path", result.stderr)
                self.assertTrue(Path(path).exists())

    def test_dotdot_path_resolving_to_system_directory_is_refused(self):
        """A path that resolves to a system directory via .. is refused."""
        result = self.safe_rm(f"{self.dir}/../../usr")
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(Path("/usr").exists())


class SafeRmDirScopeTest(unittest.TestCase):
    """safe_rm_dir: removal is limited to the data path and configured venv."""

    def setUp(self):
        self.data = make_temp_dir(self)
        self.other = Path(make_temp_dir(self))

    def test_path_outside_data_and_venv_is_refused(self):
        """A path outside the data path and venv is refused and preserved."""
        victim = self.other / "precious"
        victim.mkdir()
        (victim / "keep").write_text("x")
        result = run_omnia_function(
            f'safe_rm_dir "{victim}"',
            {"OMNIA_DATA_PATH": self.data, "OMNIA_VENV_PATH": f"{self.data}/venv"},
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("outside the Omnia data/venv paths", result.stderr)
        self.assertTrue((victim / "keep").exists())

    def test_configured_venv_outside_data_path_is_allowed(self):
        """The configured venv may live outside the data path."""
        venv = self.other / "venv"
        (venv / "bin").mkdir(parents=True)
        result = run_omnia_function(
            f'safe_rm_dir "{venv}"',
            {"OMNIA_DATA_PATH": self.data, "OMNIA_VENV_PATH": str(venv)},
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(venv.exists())


class BuildCmdTest(unittest.TestCase):
    """build_cmd: every substituted value is shell-quoted."""

    def test_clone_path_metacharacters_are_quoted(self):
        """A payload with ; and # stays a single shell argument."""
        payload = "/srv/omnia; touch /tmp/pwned #"
        cmd = build_cmd("cat_file", path=payload)
        self.assertNotIn(f" {payload}", cmd)
        script = f"set -e; f() {{ printf '%s' \"$1\"; }}; {cmd.replace('cat ', 'f ', 1)}"
        out = subprocess.run(
            ["/usr/bin/bash", "-c", script],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(out.stdout, payload)

    def test_command_substitution_is_not_expanded(self):
        """$(...) is quoted so it cannot be expanded."""
        cmd = build_cmd("file_exists", path="$(touch /tmp/pwned_ut)")
        self.assertIn("'$(touch /tmp/pwned_ut)'", cmd)

    def test_raw_placeholder_var_name_is_not_quoted(self):
        """Placeholders used as shell variable names are left unquoted."""
        cmd = build_cmd(
            "source_profile_and_check",
            profile_file="/etc/profile.d/omnia-env.sh",
            var_name="OMNIA_DATA_PATH",
        )
        self.assertIn("OMNIA_DATA_PATH", cmd)
        self.assertNotIn("'OMNIA_DATA_PATH'", cmd)

    def test_every_template_formats_without_error(self):
        """Every CMDS template can still be rendered through build_cmd."""
        for key, template in CMDS.items():
            fields = {f for _, f, _, _ in string.Formatter().parse(template) if f}
            build_cmd(key, **{f: "value" for f in fields})


if __name__ == "__main__":
    unittest.main()
