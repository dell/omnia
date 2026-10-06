#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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
"""
Create host map for ldms config file generation
"""

import argparse
import json
import logging
import os
import shutil
import time

import requests  # pylint: disable=unused-import
import urllib3  # pylint: disable=unused-import


def setup_logging(verbose=False) -> None:
    """Configure logging facility."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format='%(asctime)s %(levelname)s: %(message)s')

def load_config(config_path) -> dict:
    """Load the json config file given a file path."""
    if not os.path.exists(config_path):
        return {}
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


class LdmsdManager:  # pylint: disable=too-few-public-methods
    """Generate ldmsd config and params."""

    def __init__(self, config=None):
        self.config = config
        self.base_dir = os.path.dirname(os.path.realpath(__file__))
        self.out_dir = os.path.join(self.base_dir, "out_dir")

    def main(self):
        """Make host lists for each node type."""
        now = time.strftime("%Y%m%d-%H%M%S", time.localtime())
        logging.info("BEGIN LDMS INIT: %s", now)

        # Clean out previous
        if os.path.isdir(self.out_dir):
            logging.info("Clean out_dir: %s", self.out_dir)
            shutil.rmtree(self.out_dir)
        os.makedirs(self.out_dir, exist_ok=True)

        # PLACE HOLDER: just copy the example file for now
        shutil.copy("host_map.slurm-cluster.json", self.out_dir)


def main() -> None:
    """Parse arguments and generate the host map."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Turn on verbose output"
    )
    parser.add_argument(
        "--config", '-c',
        default='ldms_machine_config.json',
        help="Path to JSON config file"
    )
    args = parser.parse_args()

    config = load_config(args.config)
    verbose = args.verbose if args.verbose is not None else config.get("verbose", False)
    setup_logging(verbose)

    agg = LdmsdManager(config)
    agg.main()


if __name__ == '__main__':
    main()
