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
"""Command-line parsing and safety checks for the dataset generator."""

import argparse
import re

from .dataset_network import is_documentation_host, validate_hostname_or_ipv4


_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


class DatasetCliError(Exception):
    """Raised when command-line input is invalid or ambiguous."""


def validate_name(name: str, label: str) -> str:
    """Validate a dataset or profile name as one safe directory stem."""
    if not isinstance(name, str) or not _NAME_PATTERN.fullmatch(name):
        raise DatasetCliError(
            f"Invalid {label} '{name}'. Use letters, numbers, '.', '_', or '-' "
            "and start with a letter or number."
        )
    if label == "dataset name" and name == "generator":
        raise DatasetCliError("Dataset name 'generator' is reserved")
    return name


def validate_repo_host(host: str) -> str:
    """Validate a hostname or IPv4 address without scheme, port, or path."""
    value = host
    try:
        validated = validate_hostname_or_ipv4(value)
    except ValueError as exc:
        raise DatasetCliError(f"Invalid --repo-host value '{host}': {exc}") from exc
    if is_documentation_host(validated):
        raise DatasetCliError(
            "--repo-host must be a real reachable host, not a reserved "
            f"documentation value: {host}"
        )
    return validated


def create_parser() -> argparse.ArgumentParser:
    """Create the dataset generator command-line parser."""
    parser = argparse.ArgumentParser(
        description=(
            "Generate a dataset from canonical image_build_manager "
            "source YAML and small profile patches."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  ./generate_dataset.py profiles
  ./generate_dataset.py profiles internet-config
  ./generate_dataset.py create my_dataset --profile internet-config
  ./generate_dataset.py create my_offline --profile offline-config --repo-host repo.company.internal
  ./generate_dataset.py create my_ps --profile internet-config --var s3_provider=powerscale \\
      --var s3_endpoint_url=https://powerscale.company.internal
  ./generate_dataset.py create my_ssl --profile offline-catalog \\
      --set image_build_config:build_image.repo_ssl_verify=false \\
      --repo-host repo.company.internal
  ./generate_dataset.py create my_snapshot --from-src --repo-variant internet
  ./generate_dataset.py create my_dataset --profile internet-config --dry-run
  ./generate_dataset.py create my_dataset --profile internet-config --check

Legacy syntax remains supported:
  ./generate_dataset.py my_dataset internet_config

Replace the company.internal example hosts with endpoints reachable from the
execution environment.
""",
    )
    parser.add_argument("dataset_name", nargs="?", help="Dataset directory name")
    parser.add_argument("profile", nargs="?", help="Legacy positional profile name")
    parser.add_argument(
        "--profile", dest="profile_option", metavar="NAME",
        help="Profile name (default: offline-catalog)",
    )
    parser.add_argument(
        "--var", action="append", default=[], metavar="KEY=VALUE",
        help="Limited legacy flat-field alias (repeatable)",
    )
    parser.add_argument(
        "--set", dest="set_values", action="append", default=[],
        metavar="DOCUMENT:PATH=VALUE",
        help=(
            "Typed existing-field override; use dotted paths or JSON Pointer "
            "for keys such as /repositories/10.0/x86_64 (repeatable)"
        ),
    )
    parser.add_argument(
        "--list-profiles", "--profiles", action="store_true",
        help="List profiles and exit",
    )
    parser.add_argument(
        "--show-profile", metavar="NAME",
        help="Show one profile's behavior and effective patch, then exit",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Replace the complete existing dataset after staging succeeds",
    )
    parser.add_argument(
        "--from-src", action="store_true",
        help="Use canonical source values without applying a profile patch",
    )
    parser.add_argument(
        "--repo-variant", choices=["offline", "internet"],
        help="Select repo_status variant for --from-src or a custom profile",
    )
    parser.add_argument(
        "--repo-host", metavar="HOST",
        help=(
            "Replace every offline dummy repository host consistently; "
            "provide a hostname/IP without scheme or port"
        ),
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Build in staging without publishing",
    )
    parser.add_argument(
        "--check", action="store_true",
        help="Exit nonzero if an existing dataset differs from regenerated output",
    )
    parser.add_argument(
        "--no-color", action="store_true", help="Disable ANSI color output"
    )
    return parser


def validate_mode_arguments(args: argparse.Namespace) -> None:
    """Reject ambiguous CLI mode combinations."""
    if args.list_profiles or args.show_profile:
        _validate_profile_display_arguments(args)
        return
    if not args.dataset_name:
        raise DatasetCliError("dataset_name is required")
    validate_name(args.dataset_name, "dataset name")
    if args.profile and args.profile_option:
        raise DatasetCliError(
            "Choose a profile either positionally or with --profile, not both"
        )
    selected_profile = args.profile_option or args.profile
    if args.from_src and selected_profile:
        raise DatasetCliError("A profile cannot be combined with --from-src")
    if args.from_src and (args.var or args.set_values):
        raise DatasetCliError("CLI overrides cannot be combined with --from-src")
    if args.dry_run and args.check:
        raise DatasetCliError("--dry-run and --check are mutually exclusive")
    if args.check and args.force:
        raise DatasetCliError("--check and --force are mutually exclusive")


def _validate_profile_display_arguments(args: argparse.Namespace) -> None:
    """Reject generation arguments in list/show profile modes."""
    if args.list_profiles and args.show_profile:
        raise DatasetCliError(
            "Choose either --list-profiles or --show-profile, not both"
        )
    unexpected = (
        args.dataset_name
        or args.profile
        or args.profile_option
        or args.var
        or args.set_values
        or args.force
        or args.from_src
        or args.repo_variant
        or args.repo_host
        or args.dry_run
        or args.check
    )
    if unexpected:
        raise DatasetCliError(
            "Profile display commands do not accept dataset generation arguments"
        )


def normalize_cli_args(arguments: list[str]) -> list[str]:
    """Translate friendly command words while preserving the legacy CLI."""
    normalized = arguments
    if arguments:
        global_options = ["--no-color"] if "--no-color" in arguments else []
        remaining = [
            argument for argument in arguments if argument != "--no-color"
        ]
        if not remaining:
            normalized = []
        elif remaining[0] == "create":
            normalized = _normalize_create(remaining, global_options)
        elif remaining[0] == "profiles":
            normalized = _normalize_profiles(remaining, global_options)
        else:
            misplaced_commands = {"create", "profiles"}.intersection(
                remaining[1:]
            )
            if misplaced_commands:
                command = sorted(misplaced_commands)[0]
                raise DatasetCliError(
                    f"Command '{command}' must appear before its arguments"
                )
    return normalized


def _normalize_create(arguments: list[str], global_options: list[str]) -> list[str]:
    """Normalize the friendly create command."""
    if len(arguments) == 1:
        raise DatasetCliError(
            "Usage: generate_dataset.py create DATASET [OPTIONS]"
        )
    if arguments[1] in {"-h", "--help"}:
        return [*global_options, "--help"]
    if arguments[1].startswith("-"):
        raise DatasetCliError(
            "Dataset name must immediately follow the create command"
        )
    return [*global_options, *arguments[1:]]


def _normalize_profiles(
    arguments: list[str], global_options: list[str]
) -> list[str]:
    """Normalize the friendly profile discovery command."""
    if len(arguments) == 1:
        return [*global_options, "--list-profiles"]
    if len(arguments) == 2 and arguments[1] in {"-h", "--help"}:
        return [*global_options, "--help"]
    if len(arguments) == 2 and not arguments[1].startswith("-"):
        return [*global_options, "--show-profile", arguments[1]]
    raise DatasetCliError("Usage: generate_dataset.py profiles [PROFILE]")
