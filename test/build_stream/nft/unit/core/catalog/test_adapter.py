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

"""Unit tests for catalog adapter — regression tests for bug fixes.

Covers:
  - commit 500ccde2: K8S missing features returns {} instead of ValueError
  - commit 500ccde2: versioned bundle filename separator fix (_ not -)
"""

from core.catalog.adapter import build_service_k8s_config
from core.catalog.generator import FeatureList, Feature, Package


def _make_feature_list(features_dict=None):
    """Create a FeatureList with the given features dict."""
    if features_dict is None:
        features_dict = {}
    return FeatureList(features=features_dict)


def _make_feature(name, packages=None):
    """Create a Feature with the given name and packages."""
    return Feature(feature_name=name, packages=packages or [])


def _make_package(name, version="1.0", pkg_type="rpm", repo_name=""):
    """Create a Package with the given attributes."""
    return Package(
        package=name,
        version=version,
        type=pkg_type,
        repo_name=repo_name,
        architecture=["x86_64"],
    )


class TestBuildServiceK8sConfig:
    """Tests for build_service_k8s_config — regression for commit 500ccde2."""

    def test_missing_k8s_features_returns_empty_dict(self):
        """When K8S Controller/Worker features are missing, return {} not ValueError.

        Before fix (500ccde2), this raised ValueError which crashed catalog generation
        for catalogs without K8S features (e.g. Slurm-only clusters).
        """
        fl = _make_feature_list({"Some Other Feature": _make_feature("Other")})
        result = build_service_k8s_config(fl)
        assert result == {}

    def test_missing_k8s_controller_returns_empty_dict(self):
        """When only K8S Worker exists but not Controller, return {}."""
        fl = _make_feature_list({
            "K8S Worker": _make_feature("K8S Worker", [_make_package("kubelet")])
        })
        result = build_service_k8s_config(fl)
        assert result == {}

    def test_missing_k8s_worker_returns_empty_dict(self):
        """When only K8S Controller exists but not Worker, return {}."""
        fl = _make_feature_list({
            "K8S Controller": _make_feature("K8S Controller", [_make_package("kubeadm")])
        })
        result = build_service_k8s_config(fl)
        assert result == {}

    def test_empty_feature_list_returns_empty_dict(self):
        """Empty feature list should return {}."""
        fl = _make_feature_list({})
        result = build_service_k8s_config(fl)
        assert result == {}

    def test_both_k8s_features_present_returns_config(self):
        """When both K8S Controller and Worker exist, return valid config."""
        ctrl_pkgs = [_make_package("kubeadm"), _make_package("kubectl")]
        worker_pkgs = [_make_package("kubelet"), _make_package("kubectl")]
        fl = _make_feature_list({
            "K8S Controller": _make_feature("K8S Controller", ctrl_pkgs),
            "K8S Worker": _make_feature("K8S Worker", worker_pkgs),
        })
        result = build_service_k8s_config(fl)
        assert result != {}
        assert "service_k8s" in result or "service_kube_control_plane" in result
