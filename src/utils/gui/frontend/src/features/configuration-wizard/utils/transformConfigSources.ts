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
import * as yaml from 'js-yaml';
import { SLURM_CONFIG_FILE_NAMES } from '../schemas/common';

// Transform config_sources from form structure to output format
// Form structure: Array of { name, mode, yaml_content, file_path }
// Output format: Record<config_name, yaml_object | filepath>

type ConfigSourceEntry = {
  name: typeof SLURM_CONFIG_FILE_NAMES[number];
  mode: 'yaml' | 'filepath';
  yaml_content: string;
  file_path: string;
};

export const transformConfigSources = (
  entries: ConfigSourceEntry[]
): Record<string, any> => {
  const result: Record<string, any> = {};

  for (const entry of entries) {
    if (entry.mode === 'filepath') {
      if (!entry.file_path.trim()) continue;
      result[entry.name] = entry.file_path;
    } else {
      if (!entry.yaml_content.trim()) continue;
      try {
        result[entry.name] = yaml.load(entry.yaml_content);
      } catch (e) {
        console.warn(
          `[transformConfigSources] Invalid YAML for "${entry.name}", storing as raw string:`,
          e
        );
        result[entry.name] = entry.yaml_content;
      }
    }
  }

  return result;
};
