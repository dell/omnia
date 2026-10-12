# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""Regression tests for CON-004's Kubernetes version-pin agreement check,
covering the image-tag and repository-identifier regressions the original
implementation missed (RPM name/key changes were already detected)."""

import unittest

import source_loader  # noqa: F401  # pylint: disable=unused-import

from ansible.module_utils.catalog.report_renderer import check_con004


def _rpm(reponame, name):
    return {
        "name": name,
        "packagetype": "rpm",
        "sources": [{"architecture": "x86_64", "reponame": reponame, "name": "rhel",
                      "version": ["10.0"]}],
    }


def _image(name, tag, registry="registry.k8s.io"):
    return {
        "name": name,
        "packagetype": "image",
        "sources": [{"architecture": "x86_64", "name": "rhel", "version": ["10.0"],
                      "registry": registry}],
        "tag": tag,
    }


class Con004ImageTagTests(unittest.TestCase):
    """A container-image tag regression must be surfaced even when no RPM
    component's own name/key changed."""

    def test_image_tag_downgrade_relative_to_sibling_rpm_is_flagged(self):
        """kube-apiserver's image tag rolling back to 1.34 while kubelet
        stays pinned at 1.35 is a real disagreement."""
        future = {
            "packages": {
                "kubelet_1_35_1": _rpm("kubernetes-v1-35", "kubelet-1.35.1"),
                "registry.k8s.io/kube-apiserver": _image(
                    "registry.k8s.io/kube-apiserver", "v1.34.0"
                ),
            }
        }
        forward_diff = [{"op": "replace", "path": ["catalog", "packages",
                                                    "registry.k8s.io/kube-apiserver"]}]
        warnings = check_con004(future, forward_diff)
        self.assertEqual(len(warnings), 1)
        self.assertEqual(warnings[0]["constraint_id"], "CON-004")
        self.assertEqual(warnings[0]["severity"], "blocking")

    def test_agreeing_image_tags_and_rpm_versions_produce_no_warning(self):
        """No disagreement, no warning -- avoids a false positive."""
        future = {
            "packages": {
                "kubelet_1_35_1": _rpm("kubernetes-v1-35", "kubelet-1.35.1"),
                "registry.k8s.io/kube-apiserver": _image(
                    "registry.k8s.io/kube-apiserver", "v1.35.1"
                ),
            }
        }
        forward_diff = [{"op": "replace", "path": ["catalog", "packages",
                                                    "registry.k8s.io/kube-apiserver"]}]
        self.assertEqual(check_con004(future, forward_diff), [])

    def test_untouched_disagreement_is_not_reported(self):
        """A pre-existing disagreement the diff didn't touch is out of scope
        for this diff's warnings (matches the original RPM-only behavior)."""
        future = {
            "packages": {
                "kubelet_1_35_1": _rpm("kubernetes-v1-35", "kubelet-1.35.1"),
                "registry.k8s.io/kube-apiserver": _image(
                    "registry.k8s.io/kube-apiserver", "v1.34.0"
                ),
            }
        }
        forward_diff = [{"op": "replace", "path": ["catalog", "packages", "unrelated_pkg"]}]
        self.assertEqual(check_con004(future, forward_diff), [])


class Con004RepositoryIdentifierTests(unittest.TestCase):
    """A repository identifier (`reponame`) drifting out of sync with the
    package's own name/tag is itself a version-pin disagreement."""

    def test_reponame_downgrade_independent_of_rpm_name_is_flagged(self):
        """The RPM's own name still reads 1.35.1, but its `reponame` moved to
        the 1.34 repository -- this is exactly the previously-missed case."""
        future = {
            "packages": {
                "kubelet_1_35_1": _rpm("kubernetes-v1-34", "kubelet-1.35.1"),
                "registry.k8s.io/kube-apiserver": _image(
                    "registry.k8s.io/kube-apiserver", "v1.35.1"
                ),
            }
        }
        forward_diff = [{"op": "replace", "path": ["catalog", "packages", "kubelet_1_35_1"]}]
        warnings = check_con004(future, forward_diff)
        self.assertEqual(len(warnings), 1)
        self.assertEqual(warnings[0]["constraint_id"], "CON-004")
        self.assertIn("kubelet", warnings[0]["message"])

    def test_reponame_and_rpm_name_in_agreement_produce_no_warning(self):
        """A reponame that matches the RPM's own version is not a finding."""
        future = {
            "packages": {
                "kubelet_1_35_1": _rpm("kubernetes-v1-35", "kubelet-1.35.1"),
                "kubeadm_1_35_1": _rpm("kubernetes-v1-35", "kubeadm-1.35.1"),
            }
        }
        forward_diff = [{"op": "replace", "path": ["catalog", "packages", "kubelet_1_35_1"]}]
        self.assertEqual(check_con004(future, forward_diff), [])


if __name__ == "__main__":
    unittest.main()
