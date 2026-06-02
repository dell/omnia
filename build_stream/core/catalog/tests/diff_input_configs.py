#!/usr/bin/env python3
"""
Omnia Build Stream – Input Config Diff Tool

Compares two input directories (expected vs actual) and reports
per-file, per-cluster package differences.

Usage:
    python3 diff_input_configs.py \
        --expected /omnia/input \
        --actual   /tmp/adapter_output_test/input

The tool:
  1. Compares software_config.json (softwares list).
  2. Walks config/<arch>/<os>/<ver>/*.json in both directories.
  3. For each matching JSON, compares packages per cluster section.
  4. Reports missing files, extra files, and per-cluster diffs.

Package identity is the "package" field value.  Order is ignored.
"""

import argparse
import csv
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from collections import defaultdict
from datetime import datetime
from io import StringIO

# ── Colour helpers (ANSI) ────────────────────────────────────────────
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def _colour(text, colour):
    return f"{colour}{text}{RESET}"


# ── Normalise filenames so versioned names can match ─────────────────
_VERSION_RE = re.compile(
    r"^(?P<base>[a-z0-9_]+?)_v?(?P<ver>\d+\.\d+[\w.\-]*)\.json$"
)


def _canonical_name(filename):
    """
    Normalise versioned filenames for matching purposes.
    service_k8s_v1.35.1.json  ->  service_k8s__VER__.json
    service_k8s_1.35.1.json   ->  service_k8s__VER__.json
    csi_driver_powerscale.json -> csi_driver_powerscale.json (no version)
    """
    m = _VERSION_RE.match(filename)
    if m:
        return f"{m.group('base')}__VER__.json"
    return filename


# ── Package helpers ──────────────────────────────────────────────────
def _pkg_key(pkg):
    """Return a hashable identity for a package entry."""
    pkg_name = pkg.get("package", "")
    pkg_type = pkg.get("type", "")
    # For git packages, include version to distinguish same repo with different versions
    if pkg_type == 'git' and pkg.get("version"):
        return f"{pkg_name}_{pkg_type}_{pkg['version']}"
    # For image packages, include tag to distinguish same name with different tags
    if pkg_type == 'image' and pkg.get("tag"):
        return f"{pkg_name}_{pkg_type}_{pkg['tag']}"
    # Default: use package name and type
    return f"{pkg_name}_{pkg_type}"


def _pkg_display(pkg):
    """Short display string for a package."""
    parts = [pkg.get("package", "?")]
    if pkg.get("tag"):
        parts.append(f"tag={pkg['tag']}")
    if pkg.get("version"):
        parts.append(f"ver={pkg['version']}")
    parts.append(f"type={pkg.get('type', '?')}")
    return "  ".join(parts)


def _diff_packages(expected_pkgs, actual_pkgs, common_package_keys=None, first_cluster_keys=None, multi_cluster_keys=None):
    """
    Compare two lists of package dicts by 'package' field.
    Returns (only_in_expected, only_in_actual, tag_diffs).
    
    Args:
        common_package_keys: Set of package keys that are in the
            'service_k8s' cluster (common packages extracted by
            extract_common). Packages in this set that are missing
            from other clusters are not flagged as diffs.
        first_cluster_keys: Set of package keys that are in the
            corresponding *_first cluster in expected. Packages in
            this set that appear in the base cluster in actual
            are not flagged as diffs (they were merged).
        multi_cluster_keys: Set of package keys that appear in
            multiple clusters in expected. These may be moved to
            service_k8s by extract_common and should not be flagged
            as diffs when they appear in service_k8s in actual.
    """
    if common_package_keys is None:
        common_package_keys = set()
    if first_cluster_keys is None:
        first_cluster_keys = set()
    if multi_cluster_keys is None:
        multi_cluster_keys = set()
    
    exp_map = {}
    for p in expected_pkgs:
        k = _pkg_key(p)
        if k:
            exp_map[k] = p

    act_map = {}
    for p in actual_pkgs:
        k = _pkg_key(p)
        if k:
            act_map[k] = p

    # Packages only in expected, but exclude:
    # 1. those that are in service_k8s (extracted common packages)
    # 2. those from *_first clusters that were merged into the base cluster
    only_expected = {
        k: exp_map[k] 
        for k in exp_map 
        if k not in act_map 
        and k not in common_package_keys
        # If this is a _first cluster, ignore packages that are in actual
        and not (first_cluster_keys and k in first_cluster_keys)
    }
    # Packages only in actual, but exclude:
    # 1. multi-cluster packages moved to service_k8s by extract_common
    # 2. packages from *_first clusters merged into the base cluster
    only_actual = {
        k: act_map[k] 
        for k in act_map 
        if k not in exp_map 
        and k not in multi_cluster_keys 
        and k not in first_cluster_keys
    }

    tag_diffs = {}
    for k in exp_map:
        if k in act_map:
            e_tag = exp_map[k].get("tag", "")
            a_tag = act_map[k].get("tag", "")
            e_url = exp_map[k].get("url", "")
            a_url = act_map[k].get("url", "")
            # Skip URL diff if expected URL contains template syntax ({{}})
            # This is expected behavior - templates are resolved in actual output
            if e_tag != a_tag or (e_url != a_url and "{{" not in e_url):
                tag_diffs[k] = {
                    "expected": exp_map[k],
                    "actual": act_map[k],
                }

    return only_expected, only_actual, tag_diffs


# ── Load all packages from a config JSON ─────────────────────────────
def _load_config_packages(filepath):
    """
    Load a config JSON and return {section_name: [pkg_list]}.
    Each section (e.g. 'service_k8s', 'slurm_control_node') has a
    'cluster' key containing the package list.
    """
    with open(filepath) as f:
        data = json.load(f)
    sections = {}
    for key, val in data.items():
        if isinstance(val, dict) and "cluster" in val:
            sections[key] = val["cluster"]
    return sections


# ── Collect all packages across all clusters into a flat set ────────
def _all_packages_flat(sections):
    """Return a dict keyed by package name -> pkg dict, across all clusters."""
    result = {}
    for cluster_pkgs in sections.values():
        for pkg in cluster_pkgs:
            k = _pkg_key(pkg)
            if k:
                result[k] = pkg
    return result


# ── Walk config dirs and build {canonical_name -> real_path} ────────
def _scan_config_dir(config_dir):
    """
    Walk config/<arch>/<os>/<ver>/ and return:
      { (arch, os, ver, canonical_filename): real_filepath }
    """
    result = {}
    if not os.path.isdir(config_dir):
        return result
    for arch in sorted(os.listdir(config_dir)):
        arch_dir = os.path.join(config_dir, arch)
        if not os.path.isdir(arch_dir):
            continue
        for os_name in sorted(os.listdir(arch_dir)):
            os_dir = os.path.join(arch_dir, os_name)
            if not os.path.isdir(os_dir):
                continue
            for ver in sorted(os.listdir(os_dir)):
                ver_dir = os.path.join(os_dir, ver)
                if not os.path.isdir(ver_dir):
                    continue
                for fn in sorted(os.listdir(ver_dir)):
                    if fn.endswith(".json"):
                        canon = _canonical_name(fn)
                        key = (arch, os_name, ver, canon)
                        result[key] = os.path.join(ver_dir, fn)
    return result


# ── Parse PXE mapping to extract roles ──────────────────────────────────
def _parse_pxe_mapping(pxe_mapping_path):
    """
    Parse PXE mapping CSV file and return list of FUNCTIONAL_GROUP_NAME entries.
    """
    roles = []
    if not os.path.isfile(pxe_mapping_path):
        return roles

    with open(pxe_mapping_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            group_name = row.get('FUNCTIONAL_GROUP_NAME', '')
            if group_name:
                roles.append(group_name)

    return sorted(roles)


# ── Compare software_config.json ────────────────────────────────────
def _compare_software_config(expected_dir, actual_dir):
    exp_path = os.path.join(expected_dir, "software_config.json")
    act_path = os.path.join(actual_dir, "software_config.json")

    issues = []
    if not os.path.exists(exp_path):
        issues.append("Expected software_config.json not found")
        return issues
    if not os.path.exists(act_path):
        issues.append("Actual software_config.json not found")
        return issues

    with open(exp_path) as f:
        exp = json.load(f)
    with open(act_path) as f:
        act = json.load(f)

    exp_sw = {s["name"] for s in exp.get("softwares", [])}
    act_sw = {s["name"] for s in act.get("softwares", [])}

    only_exp = exp_sw - act_sw
    only_act = act_sw - exp_sw

    if only_exp:
        issues.append(f"Softwares only in expected: {sorted(only_exp)}")
    if only_act:
        issues.append(f"Softwares only in actual:   {sorted(only_act)}")
    if not only_exp and not only_act:
        issues.append("Software names match.")

    # Compare versions
    exp_ver = {s["name"]: s.get("version", "") for s in exp.get("softwares", [])}
    act_ver = {s["name"]: s.get("version", "") for s in act.get("softwares", [])}
    for name in exp_sw & act_sw:
        if exp_ver[name] != act_ver[name]:
            issues.append(
                f"  Version mismatch for '{name}': "
                f"expected={exp_ver[name]!r} actual={act_ver[name]!r}"
            )

    return issues


# ── Collect structured diff results ──────────────────────────────────
def collect_diff_results(expected_dir, actual_dir, file_level=False, pxe_mapping_path=None, catalog_path=None):
    """Return a structured dict of all diff findings.

    Args:
        expected_dir: Path to expected input directory
        actual_dir: Path to actual/generated input directory
        file_level: If True, compare at file level instead of per-cluster
        pxe_mapping_path: Optional path to PXE mapping CSV file for information
        catalog_path: Optional path to catalog file for information
    """
    results = {
        "expected_dir": expected_dir,
        "actual_dir": actual_dir,
        "software_config": _compare_software_config(expected_dir, actual_dir),
        "file_diffs": [],   # list of per-file diff dicts
        "total_issues": 0,
        "pxe_mapping_path": pxe_mapping_path,
        "pxe_roles": _parse_pxe_mapping(pxe_mapping_path) if pxe_mapping_path else [],
        "catalog_path": catalog_path,
    }

    exp_config = os.path.join(expected_dir, "config")
    act_config = os.path.join(actual_dir, "config")
    exp_files = _scan_config_dir(exp_config)
    act_files = _scan_config_dir(act_config)
    all_keys = sorted(set(exp_files.keys()) | set(act_files.keys()))

    for key in all_keys:
        arch, os_name, ver, canon = key
        exp_path = exp_files.get(key)
        act_path = act_files.get(key)
        exp_fn = os.path.basename(exp_path) if exp_path else None
        act_fn = os.path.basename(act_path) if act_path else None
        display = exp_fn or act_fn or canon
        location = f"{arch}/{os_name}/{ver}"

        entry = {
            "location": location,
            "file": display,
            "expected_name": exp_fn,
            "actual_name": act_fn,
            "status": "OK",
            "cluster_diffs": [],
            "flat_only_exp": {},
            "flat_only_act": {},
        }

        if exp_path and not act_path:
            entry["status"] = "MISSING"
            results["total_issues"] += 1
            results["file_diffs"].append(entry)
            continue
        if act_path and not exp_path:
            entry["status"] = "EXTRA"
            results["total_issues"] += 1
            results["file_diffs"].append(entry)
            continue
        if exp_fn != act_fn:
            entry["status"] = "RENAME"
            results["total_issues"] += 1

        exp_sections = _load_config_packages(exp_path)
        act_sections = _load_config_packages(act_path)

        # Extract common packages from service_k8s cluster in actual output
        # These are packages extracted by extract_common operation
        common_package_keys = set()
        if "service_k8s" in act_sections:
            for pkg in act_sections["service_k8s"]:
                k = _pkg_key(pkg)
                if k:
                    common_package_keys.add(k)

        # Extract packages from *_first clusters in expected output
        # These may be moved to base clusters by extract_common
        first_cluster_package_keys = {}
        for section in exp_sections:
            if section.endswith("_first"):
                base_section = section[:-6]  # Remove "_first" suffix
                first_keys = set()
                for pkg in exp_sections[section]:
                    k = _pkg_key(pkg)
                    if k:
                        first_keys.add(k)
                first_cluster_package_keys[base_section] = first_keys

        # Count package occurrences across all expected clusters
        # Packages appearing in multiple clusters are candidates for
        # being moved to service_k8s by extract_common
        package_occurrences = defaultdict(int)
        for section in exp_sections:
            for pkg in exp_sections[section]:
                k = _pkg_key(pkg)
                if k:
                    package_occurrences[k] += 1
        multi_cluster_keys = {k for k, count in package_occurrences.items() if count > 1}

        if file_level:
            exp_all = _all_packages_flat(exp_sections)
            act_all = _all_packages_flat(act_sections)
            only_exp = {k: v for k, v in exp_all.items() if k not in act_all}
            only_act = {k: v for k, v in act_all.items() if k not in exp_all}
            if only_exp or only_act:
                if entry["status"] == "OK":
                    entry["status"] = "DIFF"
                entry["flat_only_exp"] = only_exp
                entry["flat_only_act"] = only_act
                results["total_issues"] += len(only_exp) + len(only_act)
        else:
            all_sections = sorted(set(exp_sections.keys()) | set(act_sections.keys()))
            for section in all_sections:
                e_pkgs = exp_sections.get(section, [])
                a_pkgs = act_sections.get(section, [])
                # Get first cluster keys for this section if applicable
                # We need to pass them for BOTH the base section AND the _first section
                # so that they are ignored as diffs in both cases
                base_section = section[:-6] if section.endswith("_first") else section
                first_keys = first_cluster_package_keys.get(base_section, set())
                only_e, only_a, tag_d = _diff_packages(e_pkgs, a_pkgs, common_package_keys, first_keys, multi_cluster_keys)
                if only_e or only_a or tag_d:
                    if entry["status"] == "OK":
                        entry["status"] = "DIFF"
                    entry["cluster_diffs"].append({
                        "section": section,
                        "only_exp": only_e,
                        "only_act": only_a,
                        "tag_diffs": tag_d,
                    })
                    results["total_issues"] += len(only_e) + len(only_a) + len(tag_d)

        results["file_diffs"].append(entry)

    # Count software_config issues
    for line in results["software_config"]:
        if "only in" in line.lower() or "mismatch" in line.lower():
            results["total_issues"] += 1

    return results


# ── ANSI Console Output ──────────────────────────────────────────────
def print_ansi_report(results):
    """Print the coloured console report (original format)."""
    print(f"\n{_colour('=' * 70, BOLD)}")
    print(_colour("  Omnia Input Config Diff", BOLD + CYAN))
    print(f"{_colour('=' * 70, BOLD)}")
    print(f"  Expected: {results['expected_dir']}")
    print(f"  Actual:   {results['actual_dir']}\n")

    # Print catalog path if provided
    if results.get("catalog_path"):
        print(f"  Catalog: {results['catalog_path']}\n")

    # Print PXE mapping info if provided
    if results.get("pxe_mapping_path"):
        print(f"  PXE Mapping: {results['pxe_mapping_path']}")
        if results.get("pxe_roles"):
            print(f"  PXE Roles ({len(results['pxe_roles'])}):")
            for role in results['pxe_roles']:
                print(f"    - {role}")
        print()

    print(_colour("── software_config.json ─────────────────────────", BOLD))
    for line in results["software_config"]:
        if "only in" in line.lower() or "mismatch" in line.lower():
            print(f"  {_colour('!', YELLOW)} {line}")
        else:
            print(f"  {_colour('OK', GREEN)} {line}")

    print(f"\n{_colour('── Config Files ────────────────────────────────', BOLD)}")
    prev_loc = None
    for entry in results["file_diffs"]:
        if entry["location"] != prev_loc:
            print(f"\n  {_colour(entry['location'], BOLD + CYAN)}")
            prev_loc = entry["location"]

        st = entry["status"]
        fn = entry["file"]

        if st == "MISSING":
            print(f"    {_colour('MISSING in ACTUAL', RED)}  {fn}")
            continue
        if st == "EXTRA":
            print(f"    {_colour('NEW in ACTUAL ', YELLOW)}  {fn}")
            continue
        if entry["expected_name"] != entry["actual_name"]:
            print(f"    {_colour('RENAME', YELLOW)}  expected={entry['expected_name']}  actual={entry['actual_name']}")

        if not entry["cluster_diffs"] and not entry["flat_only_exp"] and not entry["flat_only_act"]:
            if st in ("OK", "RENAME"):
                print(f"    {_colour('OK', GREEN)}  {fn}")
            continue

        print(f"    {_colour('DIFF', RED)}   {fn}")
        # Flat mode
        if entry["flat_only_exp"]:
            print(f"      MISSING in ACTUAL ({len(entry['flat_only_exp'])})")
            for k in sorted(entry["flat_only_exp"]):
                print(f"        - {_pkg_display(entry['flat_only_exp'][k])}")
        if entry["flat_only_act"]:
            print(f"      NEW in ACTUAL ({len(entry['flat_only_act'])})")
            for k in sorted(entry["flat_only_act"]):
                print(f"        + {_pkg_display(entry['flat_only_act'][k])}")
        # Cluster mode
        for cd in entry["cluster_diffs"]:
            print(f"      [{cd['section']}]")
            for k in sorted(cd["only_exp"]):
                print(f"        {_colour('-', RED)} MISSING in ACTUAL: {_pkg_display(cd['only_exp'][k])}")
            for k in sorted(cd["only_act"]):
                print(f"        {_colour('+', GREEN)} NEW in ACTUAL: {_pkg_display(cd['only_act'][k])}")
            for k in sorted(cd["tag_diffs"]):
                e = cd["tag_diffs"][k]["expected"]
                a = cd["tag_diffs"][k]["actual"]
                print(f"        {_colour('~', YELLOW)} {k}  expected=({e.get('tag','') or e.get('url','')})  actual=({a.get('tag','') or a.get('url','')})")

    print(f"\n{_colour('=' * 70, BOLD)}")
    if results["total_issues"] == 0:
        print(_colour("  All packages match!", GREEN + BOLD))
    else:
        print(_colour(f"  {results['total_issues']} issue(s) found", RED + BOLD))
    print(f"{_colour('=' * 70, BOLD)}\n")

    print(f"{YELLOW}Note: Missing packages may be due to PXE mapping not having a ROLE for that respective architecture, please cross check.{RESET}\n")


# ── Human-Readable Table Report ──────────────────────────────────────
def _table_line(cols, widths):
    """Format a single table row."""
    parts = []
    for col, w in zip(cols, widths):
        parts.append(str(col).ljust(w))
    return "| " + " | ".join(parts) + " |"


def _table_sep(widths):
    return "+-" + "-+-".join("-" * w for w in widths) + "-+"


def generate_table_report(results):
    """Return a plain-text table-formatted report string."""
    out = StringIO()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    out.write(f"Omnia Input Config Diff Report  ({ts})\n")
    out.write(f"Expected: {results['expected_dir']}\n")
    out.write(f"Actual:   {results['actual_dir']}\n")
    out.write("=" * 100 + "\n\n")

    # Print catalog path if provided
    if results.get("catalog_path"):
        out.write(f"Catalog: {results['catalog_path']}\n\n")

    # Print PXE mapping info if provided
    if results.get("pxe_mapping_path"):
        out.write(f"PXE Mapping: {results['pxe_mapping_path']}\n")
        if results.get("pxe_roles"):
            out.write(f"PXE Roles ({len(results['pxe_roles'])}):\n")
            for role in results['pxe_roles']:
                out.write(f"  - {role}\n")
        out.write("\n")
        out.write("Note: Missing packages may be due to PXE mapping not having a ROLE for that respective architecture.\n")
        out.write("\n")
        out.write("=" * 100 + "\n\n")

    # ── software_config summary ──
    out.write("SOFTWARE_CONFIG.JSON\n")
    out.write("-" * 40 + "\n")
    for line in results["software_config"]:
        out.write(f"  {line}\n")
    out.write("\n")

    # ── File summary table ──
    out.write("FILE SUMMARY\n")
    widths = [28, 40, 8]
    out.write(_table_sep(widths) + "\n")
    out.write(_table_line(["Location", "File", "Status"], widths) + "\n")
    out.write(_table_sep(widths) + "\n")
    for entry in results["file_diffs"]:
        out.write(_table_line(
            [entry["location"], entry["file"], entry["status"]],
            widths,
        ) + "\n")
    out.write(_table_sep(widths) + "\n\n")

    # ── Detailed diffs ──
    has_details = False
    for entry in results["file_diffs"]:
        if entry["status"] in ("OK",):
            continue
        if not entry["cluster_diffs"] and not entry["flat_only_exp"] and not entry["flat_only_act"] and entry["status"] not in ("MISSING", "EXTRA", "RENAME"):
            continue

        if not has_details:
            out.write("DETAILED DIFFERENCES\n")
            out.write("=" * 100 + "\n")
            has_details = True

        out.write(f"\n  [{entry['location']}] {entry['file']}  ({entry['status']})\n")

        if entry["status"] == "RENAME":
            out.write(f"    Expected filename: {entry['expected_name']}\n")
            out.write(f"    Actual filename:   {entry['actual_name']}\n")

        if entry["status"] in ("MISSING", "EXTRA"):
            continue

        # Flat diffs
        if entry["flat_only_exp"] or entry["flat_only_act"]:
            pw = [50, 12, 16]
            out.write("    " + _table_sep(pw) + "\n")
            out.write("    " + _table_line(["Package", "Type", "Where"], pw) + "\n")
            out.write("    " + _table_sep(pw) + "\n")
            for k in sorted(entry["flat_only_exp"]):
                p = entry["flat_only_exp"][k]
                out.write("    " + _table_line([p.get("package",""), p.get("type",""), "MISSING in ACTUAL"], pw) + "\n")
            for k in sorted(entry["flat_only_act"]):
                p = entry["flat_only_act"][k]
                out.write("    " + _table_line([p.get("package",""), p.get("type",""), "NEW in ACTUAL"], pw) + "\n")
            out.write("    " + _table_sep(pw) + "\n")

        # Cluster diffs
        for cd in entry["cluster_diffs"]:
            out.write(f"    Cluster: {cd['section']}\n")
            pw = [50, 12, 16]
            out.write("    " + _table_sep(pw) + "\n")
            out.write("    " + _table_line(["Package", "Type", "Status"], pw) + "\n")
            out.write("    " + _table_sep(pw) + "\n")
            for k in sorted(cd["only_exp"]):
                p = cd["only_exp"][k]
                out.write("    " + _table_line([p.get("package",""), p.get("type",""), "MISSING in ACTUAL"], pw) + "\n")
            for k in sorted(cd["only_act"]):
                p = cd["only_act"][k]
                out.write("    " + _table_line([p.get("package",""), p.get("type",""), "NEW in ACTUAL"], pw) + "\n")
            for k in sorted(cd["tag_diffs"]):
                e = cd["tag_diffs"][k]["expected"]
                a = cd["tag_diffs"][k]["actual"]
                e_val = e.get("tag","") or e.get("url","")
                a_val = a.get("tag","") or a.get("url","")
                out.write("    " + _table_line([k, e.get("type",""), f"TAG/URL diff"], pw) + "\n")
                out.write(f"      expected: {e_val}\n")
                out.write(f"      actual:   {a_val}\n")
            out.write("    " + _table_sep(pw) + "\n")

    out.write("\n" + "=" * 100 + "\n")
    if results["total_issues"] == 0:
        out.write("RESULT: ALL PACKAGES MATCH\n")
    else:
        out.write(f"RESULT: {results['total_issues']} ISSUE(S) FOUND\n")
    out.write("=" * 100 + "\n")
    return out.getvalue()


# ── Main diff logic ──────────────────────────────────────────────────
def run_diff(expected_dir, actual_dir, file_level=False, report_file=None, print_output=True, pxe_mapping_path=None, catalog_path=None):
    """Run diff and optionally print output and write report.

    Args:
        expected_dir: Path to expected input directory
        actual_dir: Path to actual/generated input directory
        file_level: If True, compare at file level instead of per-cluster
        report_file: If provided, write table report to this file
        print_output: If True, print ANSI report to console
        pxe_mapping_path: Optional path to PXE mapping CSV file for information
        catalog_path: Optional path to catalog file for information

    Returns:
        total_issues: Number of issues found
    """
    results = collect_diff_results(expected_dir, actual_dir, file_level, pxe_mapping_path, catalog_path)

    if print_output:
        print_ansi_report(results)

    if report_file:
        table_text = generate_table_report(results)
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(table_text)
        if print_output:
            print(f"Table report written to: {report_file}")

    return results["total_issues"]


def run_diff_for_test(expected_dir, actual_dir, report_file=None, file_level=False, pxe_mapping_path=None, catalog_path=None):
    """Test-friendly diff function that generates report and returns simple pass/fail.

    This is designed to be used in test functions. It:
    - Does not print to console (to avoid cluttering test output)
    - Always generates a table report (uses temp file if report_file not provided)
    - Returns (passed, issue_count, report_path)

    Args:
        expected_dir: Path to expected input directory
        actual_dir: Path to actual/generated input directory
        report_file: Optional path to write the diff report (uses temp file if not provided)
        file_level: If True, compare at file level instead of per-cluster
        pxe_mapping_path: Optional path to PXE mapping CSV file for information
        catalog_path: Optional path to catalog file for information

    Returns:
        tuple: (passed, issue_count, report_path)
            - passed: True if no issues found, False otherwise
            - issue_count: Number of issues found
            - report_path: Path to the generated report file
    """
    # Use temporary file if report_file not provided
    if not report_file:
        fd, report_file = tempfile.mkstemp(suffix="_diff_report.txt", prefix="inputconfig_")
        os.close(fd)

    results = collect_diff_results(expected_dir, actual_dir, file_level, pxe_mapping_path, catalog_path)
    table_text = generate_table_report(results)

    with open(report_file, "w", encoding="utf-8") as f:
        f.write(table_text)

    return results["total_issues"] == 0, results["total_issues"], report_file


def main():
    parser = argparse.ArgumentParser(
        description="Omnia Build Stream – Input Config Diff Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--expected",
        required=True,
        help="Path to expected input directory (e.g. build_stream_venu_oim/input)",
    )
    parser.add_argument(
        "--actual",
        required=True,
        help="Path to actual/generated input directory (e.g. /tmp/adapter_output_test/input)",
    )
    parser.add_argument(
        "--file-level",
        action="store_true",
        default=False,
        help="Compare packages at file level (flatten all clusters) instead of per-cluster",
    )
    parser.add_argument(
        "--report",
        default=None,
        help="Write a human-readable table report to the given file path",
    )
    parser.add_argument(
        "--pxe-mapping",
        default=None,
        help="Path to PXE mapping CSV file for information display",
    )
    parser.add_argument(
        "--catalog",
        default=None,
        help="Path to catalog file for information display",
    )
    args = parser.parse_args()
    issues = run_diff(args.expected, args.actual, file_level=args.file_level, report_file=args.report, pxe_mapping_path=args.pxe_mapping, catalog_path=args.catalog)
    sys.exit(1 if issues else 0)


if __name__ == "__main__":
    main()
