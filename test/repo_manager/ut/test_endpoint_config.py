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
"""Tests for repo_manager_endpoint_config.yml schema and content validation.

Validates that repo_manager_endpoint_config.yml conforms to the actual JSON
schema at:
  src/repo_manager/plugins/module_utils/input_validation/schema/
  repo_manager_endpoint_config.json

Schema summary (repo_manager_endpoint_config.json):
  Required fields:
    - pulp_server_ip   : string
    - pulp_server_port : integer, minimum 1, maximum 65535, default 2225
    - pulp_protocol    : string, enum ["https", "http"], default "https"

  Optional fields:
    - pulp_https_enabled: boolean, default true
    - ssl_certificates  : object with optional string properties:
        server_crt, server_key, certs_dir
"""

import jsonschema
import pytest


# ---------------------------------------------------------------------------
# Schema file tests
# ---------------------------------------------------------------------------
class TestEndpointConfigSchemaFile:
    """Validate the endpoint config schema file itself."""

    def test_schema_file_exists(self, schema_dir):
        """repo_manager_endpoint_config.json schema file must exist."""
        assert (schema_dir / "repo_manager_endpoint_config.json").exists()

    def test_schema_is_valid_json(self, endpoint_config_schema):
        """Schema must be parseable JSON with expected top-level keys."""
        assert "properties" in endpoint_config_schema
        assert "type" in endpoint_config_schema
        assert endpoint_config_schema["type"] == "object"

    def test_schema_declares_required_fields(self, endpoint_config_schema):
        """Schema must declare the three required fields."""
        required = endpoint_config_schema.get("required", [])
        for field in ["pulp_server_ip", "pulp_server_port", "pulp_protocol"]:
            assert field in required, f"Schema 'required' missing '{field}'"

    def test_schema_pulp_server_ip_is_string(self, endpoint_config_schema):
        """pulp_server_ip must be typed as string."""
        prop = endpoint_config_schema["properties"]["pulp_server_ip"]
        assert prop["type"] == "string"

    def test_schema_pulp_server_port_constraints(self, endpoint_config_schema):
        """pulp_server_port must be integer with range 1-65535."""
        prop = endpoint_config_schema["properties"]["pulp_server_port"]
        assert prop["type"] == "integer"
        assert prop["minimum"] == 1
        assert prop["maximum"] == 65535

    def test_schema_pulp_protocol_enum(self, endpoint_config_schema):
        """pulp_protocol must be enum of ['https', 'http']."""
        prop = endpoint_config_schema["properties"]["pulp_protocol"]
        assert prop["type"] == "string"
        assert set(prop["enum"]) == {"https", "http"}

    def test_schema_has_ssl_certificates_object(self, endpoint_config_schema):
        """Schema must define ssl_certificates as an object."""
        props = endpoint_config_schema["properties"]
        assert "ssl_certificates" in props
        assert props["ssl_certificates"]["type"] == "object"

    def test_schema_ssl_certificates_properties(self, endpoint_config_schema):
        """ssl_certificates must define server_crt, server_key, certs_dir."""
        ssl_props = endpoint_config_schema["properties"]["ssl_certificates"]["properties"]
        for field in ["server_crt", "server_key", "certs_dir"]:
            assert field in ssl_props, (
                f"ssl_certificates schema missing property '{field}'"
            )
            assert ssl_props[field]["type"] == "string"

    def test_schema_has_pulp_https_enabled(self, endpoint_config_schema):
        """Schema must define pulp_https_enabled as boolean."""
        props = endpoint_config_schema["properties"]
        assert "pulp_https_enabled" in props
        assert props["pulp_https_enabled"]["type"] == "boolean"


# ---------------------------------------------------------------------------
# Default input file structure tests
# ---------------------------------------------------------------------------
class TestEndpointConfigStructure:
    """Validate repo_manager_endpoint_config.yml structure."""

    def test_has_pulp_server_ip(self, endpoint_config):
        """repo_manager_endpoint_config.yml must have pulp_server_ip."""
        assert "pulp_server_ip" in endpoint_config, (
            "repo_manager_endpoint_config.yml missing 'pulp_server_ip'"
        )
        assert isinstance(endpoint_config["pulp_server_ip"], str)

    def test_has_pulp_server_port(self, endpoint_config):
        """repo_manager_endpoint_config.yml must have pulp_server_port."""
        assert "pulp_server_port" in endpoint_config, (
            "repo_manager_endpoint_config.yml missing 'pulp_server_port'"
        )
        assert isinstance(endpoint_config["pulp_server_port"], int)

    def test_pulp_server_port_in_range(self, endpoint_config):
        """pulp_server_port must be between 1 and 65535."""
        port = endpoint_config["pulp_server_port"]
        assert 1 <= port <= 65535, (
            f"pulp_server_port {port} is out of range 1-65535"
        )

    def test_has_pulp_protocol(self, endpoint_config):
        """repo_manager_endpoint_config.yml must have pulp_protocol."""
        assert "pulp_protocol" in endpoint_config, (
            "repo_manager_endpoint_config.yml missing 'pulp_protocol'"
        )

    def test_pulp_protocol_is_valid_enum(self, endpoint_config):
        """pulp_protocol must be 'https' or 'http'."""
        assert endpoint_config["pulp_protocol"] in ("https", "http"), (
            f"Invalid pulp_protocol: {endpoint_config['pulp_protocol']}"
        )

    def test_has_ssl_certificates(self, endpoint_config):
        """repo_manager_endpoint_config.yml must have ssl_certificates."""
        assert "ssl_certificates" in endpoint_config, (
            "repo_manager_endpoint_config.yml missing 'ssl_certificates'"
        )

    def test_ssl_certificates_has_required_fields(self, endpoint_config):
        """ssl_certificates must have server_crt, server_key, and certs_dir."""
        ssl = endpoint_config.get("ssl_certificates", {})
        for field in ["server_crt", "server_key", "certs_dir"]:
            assert field in ssl, (
                f"ssl_certificates missing field '{field}'"
            )
            assert isinstance(ssl[field], str)

    def test_has_pulp_https_enabled(self, endpoint_config):
        """repo_manager_endpoint_config.yml must have pulp_https_enabled."""
        assert "pulp_https_enabled" in endpoint_config
        assert isinstance(endpoint_config["pulp_https_enabled"], bool)


# ---------------------------------------------------------------------------
# JSON schema validation tests (positive and negative)
# ---------------------------------------------------------------------------
class TestEndpointConfigSchemaValidation:
    """Validate data against the actual JSON schema using jsonschema."""

    def test_default_config_validates(self, endpoint_config, endpoint_config_schema):
        """The default endpoint config must validate against the schema."""
        jsonschema.validate(instance=endpoint_config, schema=endpoint_config_schema)

    def test_minimal_valid_config(self, endpoint_config_schema):
        """A minimal valid config must pass schema validation."""
        minimal = {
            "pulp_server_ip": "192.168.1.1",
            "pulp_server_port": 2225,
            "pulp_protocol": "https",
        }
        jsonschema.validate(instance=minimal, schema=endpoint_config_schema)

    def test_http_protocol_valid(self, endpoint_config_schema):
        """Config with pulp_protocol='http' must pass validation."""
        data = {
            "pulp_server_ip": "10.0.0.1",
            "pulp_server_port": 8080,
            "pulp_protocol": "http",
        }
        jsonschema.validate(instance=data, schema=endpoint_config_schema)

    def test_full_config_with_ssl(self, endpoint_config_schema):
        """Config with all optional fields must pass validation."""
        data = {
            "pulp_server_ip": "172.16.107.254",
            "pulp_server_port": 2225,
            "pulp_protocol": "https",
            "pulp_https_enabled": True,
            "ssl_certificates": {
                "server_crt": "/opt/omnia/pulp_config/certs/pulp_webserver.crt",
                "server_key": "/opt/omnia/pulp_config/certs/pulp_webserver.key",
                "certs_dir": "/opt/omnia/pulp_config/certs",
            },
        }
        jsonschema.validate(instance=data, schema=endpoint_config_schema)

    def test_port_boundary_min(self, endpoint_config_schema):
        """Port value of 1 (minimum) must pass validation."""
        data = {
            "pulp_server_ip": "10.0.0.1",
            "pulp_server_port": 1,
            "pulp_protocol": "https",
        }
        jsonschema.validate(instance=data, schema=endpoint_config_schema)

    def test_port_boundary_max(self, endpoint_config_schema):
        """Port value of 65535 (maximum) must pass validation."""
        data = {
            "pulp_server_ip": "10.0.0.1",
            "pulp_server_port": 65535,
            "pulp_protocol": "https",
        }
        jsonschema.validate(instance=data, schema=endpoint_config_schema)

    def test_missing_pulp_server_ip_fails(self, endpoint_config_schema):
        """Missing pulp_server_ip must fail validation."""
        data = {
            "pulp_server_port": 2225,
            "pulp_protocol": "https",
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=data, schema=endpoint_config_schema)

    def test_missing_pulp_server_port_fails(self, endpoint_config_schema):
        """Missing pulp_server_port must fail validation."""
        data = {
            "pulp_server_ip": "10.0.0.1",
            "pulp_protocol": "https",
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=data, schema=endpoint_config_schema)

    def test_missing_pulp_protocol_fails(self, endpoint_config_schema):
        """Missing pulp_protocol must fail validation."""
        data = {
            "pulp_server_ip": "10.0.0.1",
            "pulp_server_port": 2225,
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=data, schema=endpoint_config_schema)

    def test_invalid_protocol_fails(self, endpoint_config_schema):
        """Invalid pulp_protocol value must fail validation."""
        data = {
            "pulp_server_ip": "10.0.0.1",
            "pulp_server_port": 2225,
            "pulp_protocol": "ftp",
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=data, schema=endpoint_config_schema)

    def test_port_zero_fails(self, endpoint_config_schema):
        """Port value of 0 must fail (minimum is 1)."""
        data = {
            "pulp_server_ip": "10.0.0.1",
            "pulp_server_port": 0,
            "pulp_protocol": "https",
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=data, schema=endpoint_config_schema)

    def test_port_too_high_fails(self, endpoint_config_schema):
        """Port value of 65536 must fail (maximum is 65535)."""
        data = {
            "pulp_server_ip": "10.0.0.1",
            "pulp_server_port": 65536,
            "pulp_protocol": "https",
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=data, schema=endpoint_config_schema)

    def test_port_as_string_fails(self, endpoint_config_schema):
        """pulp_server_port as string must fail (type: integer)."""
        data = {
            "pulp_server_ip": "10.0.0.1",
            "pulp_server_port": "2225",
            "pulp_protocol": "https",
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=data, schema=endpoint_config_schema)

    def test_ip_as_integer_fails(self, endpoint_config_schema):
        """pulp_server_ip as integer must fail (type: string)."""
        data = {
            "pulp_server_ip": 12345,
            "pulp_server_port": 2225,
            "pulp_protocol": "https",
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=data, schema=endpoint_config_schema)

    def test_https_enabled_as_string_fails(self, endpoint_config_schema):
        """pulp_https_enabled as string must fail (type: boolean)."""
        data = {
            "pulp_server_ip": "10.0.0.1",
            "pulp_server_port": 2225,
            "pulp_protocol": "https",
            "pulp_https_enabled": "true",
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=data, schema=endpoint_config_schema)

    def test_negative_port_fails(self, endpoint_config_schema):
        """Negative port value must fail validation."""
        data = {
            "pulp_server_ip": "10.0.0.1",
            "pulp_server_port": -1,
            "pulp_protocol": "https",
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=data, schema=endpoint_config_schema)
