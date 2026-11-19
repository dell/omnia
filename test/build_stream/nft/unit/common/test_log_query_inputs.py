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

"""Operator log observability inputs of build_stream_config.yml (ER-BSM-003)."""

import importlib.util
import json
import sys
import types
from dataclasses import asdict
from pathlib import Path

import jsonschema
import pytest
import yaml

from api.logs import dependencies
from common.config import (
    LOG_QUERY_INPUT_KEYS,
    LogQueryConfig,
    apply_log_query_inputs,
    load_log_query_inputs,
)

pytestmark = pytest.mark.unit

SRC = Path(__file__).resolve().parents[5] / "src" / "build_stream"
CONFIG_YML = SRC / "input" / "build_stream_config.yml"
SCHEMA_JSON = (
    SRC / "plugins" / "module_utils" / "input_validation" / "schema" / "build_stream_config.json"
)
VALIDATION_DIR = SRC / "plugins" / "module_utils" / "input_validation"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(name="validator")
def fixture_validator(monkeypatch):
    """Load the L2 validator with the Ansible module_utils import path stubbed."""
    messages = _load_module(
        "bsm_messages", VALIDATION_DIR / "messages" / "build_stream_messages.py"
    )
    for name in (
        "ansible.module_utils.input_validation",
        "ansible.module_utils.input_validation.messages",
    ):
        monkeypatch.setitem(sys.modules, name, types.ModuleType(name))
    monkeypatch.setattr(
        sys.modules["ansible.module_utils.input_validation.messages"],
        "build_stream_messages",
        messages,
        raising=False,
    )
    return _load_module(
        "bsm_validator", VALIDATION_DIR / "validators" / "build_stream_config_validator.py"
    )


def _valid_config(**extra):
    return {
        "enable_build_stream": True,
        "build_stream_host_ip": "10.0.0.1",
        "build_stream_port": 8010,
        "gitlab_host": "10.0.0.2",
        **extra,
    }


class TestShippedInputFile:
    """The operator-facing YAML exposes every log input with the documented default."""

    def test_all_log_inputs_present_with_defaults(self):
        """GIVEN the shipped build_stream_config.yml THEN each log input is set to its default."""
        shipped = yaml.safe_load(CONFIG_YML.read_text(encoding="utf-8"))
        defaults = LogQueryConfig()
        for key, attr in LOG_QUERY_INPUT_KEYS.items():
            assert shipped[key] == getattr(defaults, attr), key

    def test_shipped_file_passes_schema_and_overlay(self):
        """GIVEN the shipped file with a host set THEN schema and overlay accept it."""
        shipped = yaml.safe_load(CONFIG_YML.read_text(encoding="utf-8"))
        shipped.update(build_stream_host_ip="10.0.0.1", gitlab_host="10.0.0.2")
        jsonschema.validate(shipped, json.loads(SCHEMA_JSON.read_text(encoding="utf-8")))
        assert asdict(apply_log_query_inputs(LogQueryConfig(), shipped)) == asdict(LogQueryConfig())


class TestSchema:
    """JSON schema (L1) rules for the log inputs."""

    @pytest.fixture(name="schema")
    def fixture_schema(self):
        """Parsed build_stream_config JSON schema."""
        return json.loads(SCHEMA_JSON.read_text(encoding="utf-8"))

    def test_valid_values_accepted(self, schema):
        """GIVEN in-range values THEN the schema accepts them."""
        jsonschema.validate(
            _valid_config(
                log_tail_lines_default=20, log_tail_lines_max=500, max_log_response_bytes=2048,
                log_query_rate_limit=10, log_query_max_concurrent=2,
            ),
            schema,
        )

    @pytest.mark.parametrize(
        "key,value",
        [
            ("log_tail_lines_default", 0),
            ("log_tail_lines_max", 10001),
            ("max_log_response_bytes", 100),
            ("max_log_response_bytes", 52428801),
            ("log_query_rate_limit", 0),
            ("log_query_max_concurrent", 0),
            ("log_tail_lines_default", "50"),
        ],
    )
    def test_invalid_values_rejected(self, schema, key, value):
        """GIVEN an out-of-range or mistyped value THEN the schema rejects it."""
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(_valid_config(**{key: value}), schema)


class TestSemanticValidation:
    """L2 validator cross-field rule."""

    def test_default_above_max_rejected(self, validator):
        """GIVEN default > max THEN an error names both parameters."""
        errors = validator.validate(
            _valid_config(log_tail_lines_default=600, log_tail_lines_max=500)
        )
        assert len(errors) == 1
        assert "log_tail_lines_default" in errors[0] and "log_tail_lines_max" in errors[0]

    def test_default_below_max_accepted(self, validator):
        """GIVEN default <= max THEN no error is reported."""
        assert validator.validate(
            _valid_config(log_tail_lines_default=50, log_tail_lines_max=50)
        ) == []

    def test_omitted_inputs_accepted(self, validator):
        """GIVEN no log inputs THEN defaults apply and no error is reported."""
        assert validator.validate(_valid_config()) == []


class TestCiPreviewInput:
    """log_ci_preview_lines -> GitLab CI/CD variable BSM_LOG_TAIL_LINES."""

    def test_shipped_default_is_50(self):
        """GIVEN the shipped YAML THEN the CI preview input defaults to 50."""
        shipped = yaml.safe_load(CONFIG_YML.read_text(encoding="utf-8"))
        assert shipped["log_ci_preview_lines"] == 50

    @pytest.mark.parametrize("value", [0, 10001, "50"])
    def test_schema_rejects_invalid(self, value):
        """GIVEN an out-of-range or mistyped value THEN the schema rejects it."""
        schema = json.loads(SCHEMA_JSON.read_text(encoding="utf-8"))
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(_valid_config(log_ci_preview_lines=value), schema)

    def test_preview_above_tail_max_rejected(self, validator):
        """GIVEN preview > log_tail_lines_max THEN L2 validation reports it."""
        errors = validator.validate(_valid_config(log_ci_preview_lines=600, log_tail_lines_max=500))
        assert len(errors) == 1 and "log_ci_preview_lines" in errors[0]

    def test_preview_within_tail_max_accepted(self, validator):
        """GIVEN preview <= log_tail_lines_max THEN no error is reported."""
        assert validator.validate(_valid_config(log_ci_preview_lines=100)) == []

    def test_role_pushes_input_as_gitlab_variable(self):
        """GIVEN the hosted_gitlab role THEN BSM_LOG_TAIL_LINES is sourced from the input."""
        role_vars = yaml.safe_load(
            (SRC / "roles" / "hosted_gitlab" / "vars" / "main.yml").read_text(encoding="utf-8")
        )
        entry = next(v for v in role_vars["gitlab_pipeline_bs_variables"]
                     if v["key"] == "BSM_LOG_TAIL_LINES")
        assert "log_ci_preview_lines" in entry["value"]
        assert entry["masked"] is False

    @pytest.mark.parametrize("name", [".gitlab-ci-build.yml", ".gitlab-ci-cadence.yml"])
    def test_ci_templates_do_not_hardcode_preview_lines(self, name):
        """GIVEN CI templates THEN yml defaults do not shadow the project variable."""
        text = (SRC / "roles" / "hosted_gitlab" / "files" / name).read_text(encoding="utf-8")
        assert 'BSM_LOG_TAIL_LINES: "' not in text
        assert "${BSM_LOG_TAIL_LINES:-50}" in text


class TestOverlay:
    """Runtime overlay of the operator inputs on ini/default settings."""

    def test_absent_keys_keep_base(self):
        """GIVEN no log keys THEN the base config is unchanged."""
        base = LogQueryConfig(default_tail_lines=25)
        assert apply_log_query_inputs(base, {"gitlab_host": "x"}) == base

    def test_inputs_override_base(self):
        """GIVEN log keys THEN they replace the base values."""
        config = apply_log_query_inputs(
            LogQueryConfig(),
            {
                "log_tail_lines_default": 20, "log_tail_lines_max": 500,
                "max_log_response_bytes": 2048, "log_query_rate_limit": 10,
                "log_query_max_concurrent": 2,
            },
        )
        assert (config.default_tail_lines, config.max_tail_lines) == (20, 500)
        assert config.max_response_bytes == 2048
        assert (config.rate_limit_per_minute, config.max_concurrent) == (10, 2)

    @pytest.mark.parametrize(
        "inputs",
        [
            {"log_tail_lines_default": True},
            {"log_tail_lines_default": "50"},
            {"log_query_rate_limit": 0},
            {"log_tail_lines_default": 600, "log_tail_lines_max": 500},
        ],
    )
    def test_invalid_inputs_raise(self, inputs):
        """GIVEN an invalid input THEN a ValueError is raised."""
        with pytest.raises(ValueError):
            apply_log_query_inputs(LogQueryConfig(), inputs)

    def test_missing_file_returns_base(self, tmp_path):
        """GIVEN no build_stream_config.yml THEN the base config is used."""
        base = LogQueryConfig()
        assert load_log_query_inputs(base, tmp_path / "absent.yml") is base

    def test_non_mapping_file_rejected(self, tmp_path):
        """GIVEN a YAML list THEN loading fails."""
        path = tmp_path / "build_stream_config.yml"
        path.write_text("- a\n", encoding="utf-8")
        with pytest.raises(ValueError):
            load_log_query_inputs(LogQueryConfig(), path)


class TestDependencyResolution:
    """get_log_query_config precedence and fail-safe behaviour."""

    @pytest.fixture(autouse=True)
    def _fresh_cache(self):
        dependencies.get_log_query_config.cache_clear()
        yield
        dependencies.get_log_query_config.cache_clear()

    def _point_at(self, monkeypatch, path):
        monkeypatch.setattr(dependencies, "build_stream_config_path", lambda: path)

        def _no_ini():
            raise FileNotFoundError

        monkeypatch.setattr(dependencies, "load_config", _no_ini)

    def test_yaml_inputs_win(self, tmp_path, monkeypatch):
        """GIVEN yml inputs THEN get_log_query_config reflects them."""
        path = tmp_path / "build_stream_config.yml"
        path.write_text("log_tail_lines_default: 20\nlog_query_rate_limit: 7\n", encoding="utf-8")
        self._point_at(monkeypatch, path)
        config = dependencies.get_log_query_config()
        assert (config.default_tail_lines, config.rate_limit_per_minute) == (20, 7)

    def test_invalid_yaml_inputs_fall_back(self, tmp_path, monkeypatch):
        """GIVEN an invalid input THEN the ini/default settings stay in effect."""
        path = tmp_path / "build_stream_config.yml"
        path.write_text("log_query_rate_limit: 0\nlog_tail_lines_default: 20\n", encoding="utf-8")
        self._point_at(monkeypatch, path)
        assert dependencies.get_log_query_config() == LogQueryConfig()

    def test_malformed_yaml_falls_back(self, tmp_path, monkeypatch):
        """GIVEN unparsable YAML THEN the ini/default settings stay in effect."""
        path = tmp_path / "build_stream_config.yml"
        path.write_text("log_tail_lines_default: [", encoding="utf-8")
        self._point_at(monkeypatch, path)
        assert dependencies.get_log_query_config() == LogQueryConfig()
