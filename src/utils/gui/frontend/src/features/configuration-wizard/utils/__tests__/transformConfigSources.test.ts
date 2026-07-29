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
