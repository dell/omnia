#!/usr/bin/env python3
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

"""Fill the Omnia inputs from user_inputs.yml.

    ./generate_dataset.py               replace the values in src/<domain>/input and src/main/omnia.env
    ./generate_dataset.py /abc          create /abc, copy the src inputs into it, replace there
    ./generate_dataset.py --dry-run     show what would change, write nothing

Only given values are written; an empty value keeps the source default and never
fails. The run stops when user_inputs.yml cannot be read (YAML/indentation
error), names a key the input file does not have, carries a credential, or
leaves a mandatory value empty. /opt/omnia is not touched: ./omnia.sh --init
copies the inputs there.
"""

import argparse
import sys
from pathlib import Path
from typing import List, Tuple

import yaml

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    __package__ = "dataset_generator"  # pylint: disable=redefined-builtin

# pylint: disable=wrong-import-position
from .dataset_edit import Change, EditError  # noqa: E402
from .dataset_inputs import InputError, check_inputs, load_inputs  # noqa: E402
from .dataset_publish import (  # noqa: E402
    build_outputs,
    check_output_dir,
    publish_in_place,
    publish_to_directory,
)

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
DEFAULT_INPUTS = HERE.parent / "user_inputs" / "user_inputs.yml"
PROFILES = HERE / "profiles"


class UsageError(Exception):
    """The run cannot continue; the message tells the user what to fix."""


def load_profile(name: str) -> dict:
    """Load a profile from profiles/<name>.yml."""
    path = PROFILES / f"{name}.yml"
    if not path.is_file():
        known = ", ".join(sorted(p.stem for p in PROFILES.glob("*.yml")))
        raise UsageError(f"unknown profile {name!r} (known: {known})")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def print_report(where: str, report: List[Tuple[str, str]], changes: List[Change],
                 dry_run: bool) -> None:
    """Print the files written and every value set."""
    print(f"profile -> {where}{'  [DRY RUN - nothing written]' if dry_run else ''}")
    for name, action in report:
        if action.startswith("replaced"):
            print(f"  replaced   {name}  <- {action[len('replaced '):]}")
        else:
            print(f"  {action:10} {name}")
    print(f"\n{len(changes)} value(s) set:")
    for label, key, old, new in changes:
        print(f"  {Path(label).name}: {key}: {old!r} -> {new!r}")


def run(args: argparse.Namespace) -> int:
    """Check the inputs, build the new files and publish them in src or in a folder."""
    repo_root = Path(args.repo_root).resolve()
    inputs_path = Path(args.inputs)
    profile = load_profile(args.profile)
    output_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else None
    try:
        inputs = load_inputs(inputs_path)
        check_inputs(inputs, profile.get("mandatory", []), inputs_path)
        if output_dir:
            check_output_dir(output_dir, repo_root)
        outputs, changes = build_outputs(repo_root, profile, inputs, complete=bool(output_dir))
        report = (publish_to_directory(output_dir, outputs, args.dry_run) if output_dir
                  else publish_in_place(repo_root, profile, outputs, args.dry_run))
    except (InputError, EditError, OSError, ValueError) as exc:
        raise UsageError(str(exc)) from exc
    print_report(str(output_dir or f"{repo_root}/src (in place)"), report, changes, args.dry_run)
    return 0


def main(argv: List[str] = None) -> int:
    """Run the command line."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", maxsplit=1)[0])
    parser.add_argument("output_dir", nargs="?",
                        help="create this directory with the src inputs and replace there "
                             "(default: replace in src)")
    parser.add_argument("--inputs", default=str(DEFAULT_INPUTS),
                        help="user inputs file (default: ../user_inputs/user_inputs.yml)")
    parser.add_argument("--profile", default="build_stream")
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument("--dry-run", action="store_true")
    try:
        return run(parser.parse_args(argv))
    except UsageError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
