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

"""Unit tests for generate_omnia_config."""

# pylint: disable=missing-function-docstring,redefined-outer-name
from backend.services.config_file_generators import generate_omnia_config


class TestGenerateOmniaConfig:
    """Tests for generate_omnia_config generator."""

    def test_emits_slurm_cluster_when_present(self, tmp_path, noop_write_yaml):
        wizard_data = {
            "slurm_cluster": [{"cluster_name": "test", "partition": "normal"}],
        }
        generate_omnia_config(wizard_data, tmp_path, noop_write_yaml)
        output = tmp_path / "omnia_config.yml"
        assert output.exists()
        assert "slurm_cluster" in output.read_text()

    def test_skips_when_empty(self, tmp_path, noop_write_yaml):
        generate_omnia_config({}, tmp_path, noop_write_yaml)
        assert not (tmp_path / "omnia_config.yml").exists()

    def test_skips_slurm_with_empty_cluster_name(self, tmp_path, noop_write_yaml):
        wizard_data = {"slurm_cluster": [{"cluster_name": "", "partition": "normal"}]}
        generate_omnia_config(wizard_data, tmp_path, noop_write_yaml)
        assert not (tmp_path / "omnia_config.yml").exists()

    def test_emits_k8s_cluster_when_present(self, tmp_path, noop_write_yaml):
        wizard_data = {
            "service_k8s_cluster": [
                {"cluster_name": "k8s_test", "deployment": "rke2"}
            ],
        }
        generate_omnia_config(wizard_data, tmp_path, noop_write_yaml)
        output = tmp_path / "omnia_config.yml"
        assert output.exists()
        assert "service_k8s_cluster" in output.read_text()
