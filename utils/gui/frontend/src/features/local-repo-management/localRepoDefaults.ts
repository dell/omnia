export const DEFAULT_OMNIA_REPO_X86_64 = [
  { url: "https://download.docker.com/linux/centos/10/x86_64/stable/", gpgkey: "https://download.docker.com/linux/centos/gpg", name: "docker-ce" },
  { url: "https://dl.fedoraproject.org/pub/epel/10/Everything/x86_64/", gpgkey: "https://dl.fedoraproject.org/pub/epel/RPM-GPG-KEY-EPEL-10", name: "epel" },
  { url: "https://pkgs.k8s.io/core:/stable:/v1.35/rpm/", gpgkey: "https://pkgs.k8s.io/core:/stable:/v1.35/rpm/repodata/repomd.xml.key", name: "kubernetes-v1-35" },
  { url: "https://download.opensuse.org/repositories/isv:/cri-o:/stable:/v1.35/rpm/", gpgkey: "https://download.opensuse.org/repositories/isv:/cri-o:/stable:/v1.35/rpm/repodata/repomd.xml.key", name: "cri-o-v1-35" },
  { url: "https://linux.mellanox.com/public/repo/doca/3.2.1/rhel10/x86_64/", gpgkey: "https://linux.mellanox.com/public/repo/doca/3.2.1/rhel10/x86_64/repodata/repomd.xml.key", name: "doca" },
  { url: "https://developer.download.nvidia.com/compute/cuda/repos/rhel10/x86_64/", gpgkey: "https://developer.download.nvidia.com/compute/cuda/repos/rhel10/x86_64/repodata/repomd.xml.key", name: "cuda" },
  { url: "https://developer.download.nvidia.com/hpc-sdk/rhel/x86_64", gpgkey: "https://developer.download.nvidia.com/hpc-sdk/rhel/RPM-GPG-KEY-NVIDIA-HPC-SDK", name: "nvidia-hpc-sdk" }
];

export const DEFAULT_OMNIA_REPO_AARCH64 = [
  { url: "https://download.docker.com/linux/centos/10/aarch64/stable/", gpgkey: "https://download.docker.com/linux/centos/gpg", name: "docker-ce" },
  { url: "https://dl.fedoraproject.org/pub/epel/10/Everything/aarch64/", gpgkey: "https://dl.fedoraproject.org/pub/epel/RPM-GPG-KEY-EPEL-10", name: "epel" },
  { url: "https://linux.mellanox.com/public/repo/doca/3.2.1/rhel10/arm64-sbsa/", gpgkey: "https://linux.mellanox.com/public/repo/doca/3.2.1/rhel10/arm64-sbsa/repodata/repomd.xml.key", name: "doca" },
  { url: "https://developer.download.nvidia.com/compute/cuda/repos/rhel10/sbsa/", gpgkey: "https://developer.download.nvidia.com/compute/cuda/repos/rhel10/sbsa/repodata/repomd.xml.key", name: "cuda" },
  { url: "https://developer.download.nvidia.com/hpc-sdk/rhel/aarch64", gpgkey: "https://developer.download.nvidia.com/hpc-sdk/rhel/RPM-GPG-KEY-NVIDIA-HPC-SDK", name: "nvidia-hpc-sdk" }
];
