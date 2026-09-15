# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""Readiness gate shared by Slurm feature verification suites."""

import pytest

from fvt.check.feature_helpers import slurm_data_node_ips


@pytest.mark.slurm
@pytest.mark.sanity
@pytest.mark.buildstream
@pytest.mark.order(29)
def test_slurm_feature_targets_resolve(host):
    """ORCH_FVT_SLURM_V052: Slurm feature tests resolve at least one data node."""
    targets = slurm_data_node_ips(host)
    assert targets
    assert all(name and address for name, address in targets)
