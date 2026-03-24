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

"""Catalog parser models.

Contains the dataclass-based in-memory representations of catalog components.
"""

from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Package:
    """Generic package entry from the catalog.

    Represents a single software package with name, version, supported OS list,
    architecture list, and optional source metadata.
    """

    id: str
    name: str
    version: str
    supported_os: List[str]
    uri: str
    architecture: List[str]
    type: str
    tag: str = ""
    sources: Optional[List[dict]] = None

@dataclass
class FunctionalPackage(Package):
    """Package that belongs to the functional layer of the catalog."""

@dataclass
class OsPackage(Package):
    """Package that belongs to the base OS layer of the catalog."""

@dataclass
class InfrastructurePackage:
    """Infrastructure package as described in the catalog."""

    def __init__(self, id, name, version, uri, architecture, config, type, sources=None, tag=""):
        self.id = id
        self.name = name
        self.version = version
        self.uri = uri
        self.architecture = architecture
        self.config = config
        self.type = type
        self.sources = sources
        self.tag = tag

@dataclass
class Driver:
    """Driver package entry used by the drivers layer of the catalog."""

    def __init__(self, id, name, version, uri, architecture, config, type):
        self.id = id
        self.name = name
        self.version = version
        self.uri = uri
        self.architecture = architecture
        self.config = config
        self.type = type

@dataclass
class Catalog:
    """Top-level in-memory representation of the catalog JSON.

    Holds raw layer sections and the resolved package objects used by
    generator and adapter components.
    """

    name: str
    version: str
    functional_layer: List[dict]
    base_os: List[dict]
    infrastructure: List[dict]
    drivers_layer: List[dict]
    drivers: List[Driver]
    functional_packages: List[FunctionalPackage]
    os_packages: List[OsPackage]
    infrastructure_packages: List[InfrastructurePackage]
    miscellaneous: List[str]