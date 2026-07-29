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
