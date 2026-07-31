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
import { describe, it, expect } from 'vitest'
import { transformConfigSources } from '../transformConfigSources'

describe('transformConfigSources', () => {
  it('transforms filepath mode entry', () => {
    const entries = [
      { name: 'slurm' as const, mode: 'filepath' as const, yaml_content: '', file_path: '/etc/slurm.conf' },
    ]
    const result = transformConfigSources(entries)
    expect(result.slurm).toBe('/etc/slurm.conf')
  })

  it('transforms yaml mode entry', () => {
    const entries = [
      { name: 'cgroup' as const, mode: 'yaml' as const, yaml_content: 'key: value', file_path: '' },
    ]
    const result = transformConfigSources(entries)
    expect(result.cgroup).toEqual({ key: 'value' })
  })

  it('skips empty filepath entries', () => {
    const entries = [
      { name: 'slurm' as const, mode: 'filepath' as const, yaml_content: '', file_path: '   ' },
    ]
    const result = transformConfigSources(entries)
    expect(result.slurm).toBeUndefined()
  })

  it('skips empty yaml entries', () => {
    const entries = [
      { name: 'cgroup' as const, mode: 'yaml' as const, yaml_content: '  ', file_path: '' },
    ]
    const result = transformConfigSources(entries)
    expect(result.cgroup).toBeUndefined()
  })

  it('stores invalid YAML as raw string', () => {
    const entries = [
      { name: 'slurm' as const, mode: 'yaml' as const, yaml_content: 'invalid: [yaml: {broken', file_path: '' },
    ]
    const result = transformConfigSources(entries)
    expect(typeof result.slurm).toBe('string')
  })

  it('handles multiple entries', () => {
    const entries = [
      { name: 'slurm' as const, mode: 'filepath' as const, yaml_content: '', file_path: '/etc/slurm.conf' },
      { name: 'cgroup' as const, mode: 'yaml' as const, yaml_content: 'a: 1', file_path: '' },
    ]
    const result = transformConfigSources(entries)
    expect(result.slurm).toBe('/etc/slurm.conf')
    expect(result.cgroup).toEqual({ a: 1 })
  })

  it('returns empty object for empty input', () => {
    const result = transformConfigSources([])
    expect(result).toEqual({})
  })
})
