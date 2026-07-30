// Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
// Transform node_hardware_defaults from form structure to output format
// Form structure: Array of { group_name, sockets, cores_per_socket, threads_per_core, real_memory, gres }
// Output format: Record<group_name, { Sockets, CoresPerSocket, ThreadsPerCore, RealMemory, Gres }>

type NodeHardwareDefaultsEntry = {
  group_name: string;
  sockets: number | string;
  cores_per_socket: number | string;
  threads_per_core: number | string;
  real_memory: number | string;
  gres: string;
};

export const transformNodeHardwareDefaults = (
  entries: NodeHardwareDefaultsEntry[]
): Record<string, any> => {
  const result: Record<string, any> = {};

  for (const entry of entries) {
    const group: Record<string, any> = {
      sockets: Number(entry.sockets),
      cores_per_socket: Number(entry.cores_per_socket),
      threads_per_core: Number(entry.threads_per_core),
      real_memory: Number(entry.real_memory),
    };

    if (entry.gres && entry.gres.trim()) {
      group.gres = entry.gres;
    }

    result[entry.group_name] = group;
  }

  return result;
};
