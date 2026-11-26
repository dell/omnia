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

"""Generate the trigger jobs of the parent pipeline from ``pipeline_config.yml`` (standard library only).

The first job of the parent pipeline runs this script in the GitLab project (nothing but the YAML
files, this script and ``pipeline_config.yml`` is uploaded). It reads ``pipeline_config.yml`` of the
commit being run and writes ``generated-triggers.yml``, a child pipeline whose jobs trigger the
cluster, utils or build stream pipeline of every cluster with the values of the file as their
variables. Editing and committing ``pipeline_config.yml`` is therefore enough: no CI/CD variable of
the project has to be changed. The OIM password, the host key, the OpenBao and mail credentials
stay CI/CD variables, which the child pipelines inherit.

For every setting the first non-empty value of these wins: the config file, the CI/CD variable of
the project with the old name (``<CLUSTER>_PIPELINE_MODE``, ``CLUSTERS``, ...), the default. An
empty value in the file therefore keeps the project variable, which makes the file optional.

    pipeline_triggers.py [--config pipeline_config.yml] [--out generated-triggers.yml]
"""

import argparse
import os
import re
import sys
from typing import Dict, List, Mapping, Optional, Tuple

CLUSTER_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")
ENABLED = ("true", "false")
UTILS_MODES = ("default_logs", "install_os", "collect", "backup_oim_logs")
PIPELINE_MODES = ("default", "deploy", "cleanup")
DOMAIN_TAG_KEYS = ("repo_manager", "image_build_manager", "discovery", "orchestrator", "telemetry",
                   "build_stream")
TEST_KEYS = {"test_main": "TEST_MAIN_CMD", "repo_manager": "TEST_REPO_MANAGER_CMD",
             "image_build_manager": "TEST_IMAGE_BUILD_MANAGER_CMD",
             "discovery": "TEST_DISCOVERY_CMD", "orchestrator": "TEST_ORCHESTRATOR_CMD",
             "telemetry": "TEST_TELEMETRY_CMD", "build_stream": "TEST_BUILD_STREAM_CMD",
             "utils": "TEST_UTILS_CMD"}
# (section, key, variable of the child pipeline, default)
CLUSTER_SETTINGS: Tuple[Tuple[str, str, str, str], ...] = (
    ("omnia", "repo", "OMNIA_REPO", ""),
    ("omnia", "branch", "OMNIA_BRANCH", ""),
    ("omnia", "install_path", "OMNIA_INSTALL_PATH", "/root/omnia"),
    ("omnia", "checkout_mode", "CHECKOUT_MODE", ""),
    ("vault", "server_url", "BAO_SERVER_URL", ""),
    ("vault", "auth_role", "BAO_AUTH_ROLE", ""),
    ("vault", "secret_path", "BAO_DATA_PATH", ""),
    ("pipeline", "pipeline_mode", "PIPELINE_MODE", "default"),
    ("pipeline", "domains", "DOMAINS", "default"),
    ("pipeline", "enable_setup", "ENABLE_SETUP", "false"),
    ("pipeline", "enable_discovery", "ENABLE_DISCOVERY", "false"),
    ("pipeline", "test_mode", "TEST_MODE", "true"),
    ("pipeline", "dry_run", "DRY_RUN", "false"),
    ("pipeline", "verbose", "VERBOSE", "false"),
    ("pipeline", "skip_stages", "SKIP_STAGES", ""),
    ("pipeline", "tolerate_failures", "TOLERATE_FAILURES", ""),
)
GLOBAL_SETTINGS: Tuple[Tuple[str, str, str], ...] = (
    ("email", "recipients", "EMAIL_RECIPIENTS"), ("email", "sender", "EMAIL_SENDER"),
    ("email", "smtp_server", "SMTP_SERVER"), ("email", "smtp_port", "SMTP_PORT"),
)


class ConfigError(ValueError):
    """The configuration file or one of its values is not valid."""


def parse_config(text: str) -> Dict[str, Dict]:
    """Parse the mapping subset of YAML that pipeline_config.yml uses.

    Nested ``key:`` mappings (by indentation) and ``key: value`` scalars, quoted or bare, with
    ``#`` comments. Lists, anchors and multi-line values are rejected. Every value is a string.
    """
    root: Dict[str, Dict] = {}
    stack: List[Tuple[int, Dict]] = [(-1, root)]
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if "\t" in line[: len(line) - len(line.lstrip())]:
            raise ConfigError(f"line {number}: tabs are not allowed in the indentation")
        indent = len(line) - len(line.lstrip())
        match = re.match(r"^([A-Za-z0-9_.-]+):(?:\s+(.*))?$", line.strip())
        if not match:
            raise ConfigError(f"line {number}: expected 'key: value', got {line.strip()[:60]!r}")
        key, value = match.group(1), (match.group(2) or "").strip()
        while stack and stack[-1][0] >= indent:
            stack.pop()
        if not stack:
            raise ConfigError(f"line {number}: bad indentation")
        parent = stack[-1][1]
        if value == "" or value.startswith("#"):
            child: Dict = {}
            parent[key] = child
            stack.append((indent, child))
        else:
            parent[key] = _scalar(value, number)
    return root


def _scalar(value: str, number: int) -> str:
    if value[0] in "\"'":
        quote = value[0]
        end = value.find(quote, 1)
        while quote == '"' and end > 0 and value[end - 1] == "\\":
            end = value.find(quote, end + 1)
        if end < 0:
            raise ConfigError(f"line {number}: unterminated quote")
        rest = value[end + 1:].strip()
        if rest and not rest.startswith("#"):
            raise ConfigError(f"line {number}: text after the closing quote")
        inner = value[1:end]
        return inner.replace('\\"', '"').replace("\\\\", "\\") if quote == '"' else inner
    if value[0] in "[{&*|>!":
        raise ConfigError(f"line {number}: lists, anchors and block scalars are not supported")
    return re.split(r"\s+#", value, maxsplit=1)[0].strip()


def _section(cfg: Mapping, *names: str) -> Mapping:
    node: object = cfg
    for name in names:
        node = node.get(name, {}) if isinstance(node, Mapping) else {}
    return node if isinstance(node, Mapping) else {}


def _pick(config_value: Optional[str], env_value: Optional[str], default: str) -> Tuple[str, str]:
    """Return (value, source): the config file, the project variable or the default."""
    if config_value not in (None, ""):
        return str(config_value), "config"
    if env_value not in (None, ""):
        return str(env_value), "variable"
    return default, "default"


def _check(name: str, value: str) -> str:
    """Validate a value that rules or scripts depend on, return it."""
    if name in ("ENABLE_SETUP", "ENABLE_DISCOVERY", "TEST_MODE", "DRY_RUN", "VERBOSE") \
            and value not in ENABLED:
        raise ConfigError(f"{name} must be true or false, got {value!r}")
    if name == "PIPELINE_MODE" and value not in PIPELINE_MODES:
        raise ConfigError(f"PIPELINE_MODE must be one of {', '.join(PIPELINE_MODES)}, got {value!r}")
    if name == "UTILS_MODE" and value not in UTILS_MODES:
        raise ConfigError(f"UTILS_MODE must be one of {', '.join(UTILS_MODES)}, got {value!r}")
    if name == "SMTP_PORT" and not (value.isdigit() and 0 < int(value) < 65536):
        raise ConfigError(f"SMTP_PORT must be a port number, got {value!r}")
    if "\n" in value or "\r" in value or "\x00" in value:
        raise ConfigError(f"{name} has a control character")
    return value


def email_variables(cfg: Mapping) -> Dict[str, str]:
    """Return the email settings set in the config file; an empty one keeps the project variable."""
    out: Dict[str, str] = {}
    for scope, key, name in GLOBAL_SETTINGS:
        value = _section(cfg, "global", scope).get(key)
        if value not in (None, ""):
            out[name] = _check(name, str(value))
    return out


def global_settings(cfg: Mapping, env: Mapping[str, str]) -> Dict[str, Tuple[str, str]]:
    """Return {name: (value, source)} of CLUSTERS, UTILS_ENABLE, UTILS_MODE, BUILD_STREAM_ENABLE."""
    scope = _section(cfg, "global")
    out = {
        "CLUSTERS": _pick(scope.get("clusters"), env.get("CLUSTERS"), ""),
        "UTILS_ENABLE": _pick(scope.get("utils_enable"), env.get("UTILS_ENABLE"), "false"),
        "UTILS_MODE": _pick(scope.get("utils_mode"), env.get("UTILS_MODE"), "default_logs"),
        "BUILD_STREAM_ENABLE": _pick(scope.get("build_stream_enable"),
                                     env.get("BUILD_STREAM_ENABLE"), "false"),
    }
    for flag in ("UTILS_ENABLE", "BUILD_STREAM_ENABLE"):
        if out[flag][0] not in ENABLED:
            raise ConfigError(f"{flag} must be true or false, got {out[flag][0]!r}")
    _check("UTILS_MODE", out["UTILS_MODE"][0])
    return out


def clusters_of(settings: Mapping[str, Tuple[str, str]]) -> List[str]:
    """Return the validated cluster names of CLUSTERS."""
    names = [c.strip() for c in settings["CLUSTERS"][0].split(",") if c.strip()]
    if not names:
        raise ConfigError("no cluster: set global.clusters in pipeline_config.yml (or CLUSTERS)")
    for name in names:
        if not CLUSTER_RE.match(name):
            raise ConfigError(f"cluster name {name!r} is not a plain name")
    return names


def cluster_variables(cfg: Mapping, cluster: str, env: Mapping[str, str],
                      kind: str) -> Dict[str, Tuple[str, str]]:
    """Return {variable: (value, source)} passed to the pipeline of ``kind`` for ``cluster``."""
    prefix = cluster.upper().replace("-", "_")
    scope = _section(cfg, cluster)
    if not scope:
        raise ConfigError(f"pipeline_config.yml has no section '{cluster}:' for the cluster")
    out: Dict[str, Tuple[str, str]] = {"CLUSTER": (cluster, "config")}
    conn = _section(scope, "connection")
    for key, name in (("target_ip", "TARGET_IP"), ("target_user", "TARGET_USER")):
        value, source = _pick(conn.get(key), env.get(f"{prefix}_{name}"), "")
        if value:
            out[f"{prefix}_{name}"] = (value, source)
    for section, key, name, default in CLUSTER_SETTINGS:
        value, source = _pick(_section(scope, section).get(key), env.get(f"{prefix}_{name}"),
                              default)
        if value or name in ("SKIP_STAGES", "TOLERATE_FAILURES"):
            out[name] = (_check(name, value), source)
    for domain in DOMAIN_TAG_KEYS:
        name = f"{domain.upper()}_TAGS"
        value, source = _pick(_section(scope, "deploy_tags").get(domain),
                              env.get(f"{prefix}_{name}"), "")
        if value:
            out[name] = (_check(name, value), source)
    for key, name in TEST_KEYS.items():
        value, source = _pick(_section(scope, "test_commands").get(key),
                              env.get(f"{prefix}_{name}"), "")
        if value:
            out[name] = (_check(name, value), source)
    if kind == "utils":
        mode = global_settings(cfg, env)
        out["UTILS_ENABLE"], out["UTILS_MODE"] = mode["UTILS_ENABLE"], mode["UTILS_MODE"]
    return out


def _yaml_text(value: str) -> str:
    """Return the value as a double-quoted YAML scalar; ``$`` is escaped so it stays literal."""
    escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("$", "$$")
    return f'"{escaped}"'


def kind_of(settings: Mapping[str, Tuple[str, str]]) -> str:
    """Return the pipeline to run: build_stream, then utils, else cluster (the old precedence)."""
    if settings["BUILD_STREAM_ENABLE"][0] == "true":
        return "build_stream"
    return "utils" if settings["UTILS_ENABLE"][0] == "true" else "cluster"


def render_triggers(cfg: Mapping, env: Mapping[str, str]) -> Tuple[str, List[str]]:
    """Return (text of generated-triggers.yml, one line per variable for the log)."""
    settings = global_settings(cfg, env)
    kind = kind_of(settings)
    files = {"cluster": ".gitlab-ci-cluster.yml", "build_stream": ".gitlab-ci-build-stream.yml",
             "utils": ".gitlab-ci-utils.yml"}
    suffix = {"cluster": "", "build_stream": "_build_stream", "utils": "_utils"}[kind]
    out = ["# GENERATED by pipeline_triggers.py from pipeline_config.yml, do not edit.", "stages:",
           "  - trigger", ""]
    log = [f"Pipeline: {kind} ({files[kind]}), clusters: {settings['CLUSTERS'][0]}"]
    email = email_variables(cfg)
    for cluster in clusters_of(settings):
        values = cluster_variables(cfg, cluster, env, kind)
        out += [f"trigger_cluster_{cluster}{suffix}:", "  stage: trigger",
                f"  resource_group: pipeline-{cluster}", "  trigger:", "    include:",
                f"      - local: {files[kind]}", "    strategy: depend", "  variables:"]
        out += [f"    {name}: {_yaml_text(value)}" for name, (value, _) in values.items()]
        out += [f"    {name}: {_yaml_text(value)}" for name, value in email.items()]
        out.append("")
        log += [f"  [{cluster}] {name} = {value or '(empty)'}  <{source}>"
                for name, (value, source) in values.items()]
    log += [f"  [global] {name} set in pipeline_config.yml, passed to every pipeline" for name in email]
    return "\n".join(out), log


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", maxsplit=1)[0])
    parser.add_argument("--config", default="pipeline_config.yml")
    parser.add_argument("--out", default="generated-triggers.yml")
    args = parser.parse_args(argv)
    try:
        with open(args.config, encoding="utf-8") as handle:
            cfg = parse_config(handle.read())
        text, log = render_triggers(cfg, os.environ)
    except (OSError, ConfigError) as exc:
        print(f"ERROR: {args.config}: {exc}", file=sys.stderr)
        return 1
    with open(args.out, "w", encoding="utf-8") as handle:
        handle.write(text + "\n")
    print("\n".join(log))
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
