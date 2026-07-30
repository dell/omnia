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
import { useQuery } from '@tanstack/react-query';

interface BundleInfo {
  name: string;
  type: string;
  package_count: number;
  sections: string[];
}

const API_BASE = '/api/v1/catalog-editor';

export const useAvailableBundles = (
  arch: string,
  osFamily: string,
  version: string
) => {
  return useQuery({
    queryKey: ['bundles', arch, osFamily, version],
    queryFn: async (): Promise<BundleInfo[]> => {
      const res = await fetch(
        `${API_BASE}/os-packages/bundles?arch=${arch}&os_family=${osFamily}&version=${version}`
      );
      if (!res.ok) throw new Error('Failed to fetch bundles');
      const data = await res.json();
      return data.bundles;
    },
    enabled: !!arch && !!osFamily && !!version,
  });
};

