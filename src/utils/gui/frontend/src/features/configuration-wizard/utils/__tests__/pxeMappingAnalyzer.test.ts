import { describe, it, expect } from 'vitest'
import { analyzePxeMapping } from '../pxeMappingAnalyzer'
import type { PxeMappingRow } from '../csvParser'

const makeRow = (overrides: Partial<PxeMappingRow> = {}): PxeMappingRow => ({
  FUNCTIONAL_GROUP_NAME: 'slurm_node_x86_64',
  GROUP_NAME: 'group1',
  SERVICE_TAG: 'SVC001',
  HOSTNAME: 'node01',
  ADMIN_MAC: 'AA:BB:CC:DD:EE:01',
  ADMIN_IP: '10.0.0.10',
  BMC_MAC: 'AA:BB:CC:DD:EE:02',
  BMC_IP: '10.0.1.10',
  IB_NIC_NAME: '',
  IB_IP: '',
  ...overrides,
})

describe('analyzePxeMapping', () => {
  it('returns null clusterType for empty data', () => {
    const result = analyzePxeMapping([])
    expect(result.clusterType).toBeNull()
  })

  it('detects slurm cluster type', () => {
    const rows = [makeRow({ FUNCTIONAL_GROUP_NAME: 'slurm_node_x86_64' })]
    const result = analyzePxeMapping(rows)
    expect(result.clusterType).toBe('slurm')
  })

  it('detects k8s cluster type', () => {
    const rows = [makeRow({ FUNCTIONAL_GROUP_NAME: 'service_kube_node_x86_64' })]
    const result = analyzePxeMapping(rows)
    expect(result.clusterType).toBe('k8s')
  })

  it('detects both cluster type', () => {
    const rows = [
      makeRow({ FUNCTIONAL_GROUP_NAME: 'slurm_node_x86_64' }),
      makeRow({ FUNCTIONAL_GROUP_NAME: 'service_kube_node_x86_64', SERVICE_TAG: 'SVC002', ADMIN_IP: '10.0.0.11' }),
    ]
    const result = analyzePxeMapping(rows)
    expect(result.clusterType).toBe('both')
  })

  it('extracts admin IPs', () => {
    const rows = [
      makeRow({ ADMIN_IP: '10.0.0.10' }),
      makeRow({ SERVICE_TAG: 'SVC002', ADMIN_IP: '10.0.0.11' }),
    ]
    const result = analyzePxeMapping(rows)
    expect(result.networkInfo.adminIps).toContain('10.0.0.10')
    expect(result.networkInfo.adminIps).toContain('10.0.0.11')
  })

  it('extracts BMC IPs', () => {
    const rows = [makeRow({ BMC_IP: '10.0.1.10' })]
    const result = analyzePxeMapping(rows)
    expect(result.networkInfo.bmcIps).toContain('10.0.1.10')
  })

  it('skips invalid IPs', () => {
    const rows = [makeRow({ ADMIN_IP: 'not-an-ip' })]
    const result = analyzePxeMapping(rows)
    expect(result.networkInfo.adminIps).toHaveLength(0)
  })

  it('detects admin subnet', () => {
    const rows = [
      makeRow({ ADMIN_IP: '10.0.0.10' }),
      makeRow({ SERVICE_TAG: 'SVC002', ADMIN_IP: '10.0.0.20' }),
    ]
    const result = analyzePxeMapping(rows)
    expect(result.networkInfo.adminSubnet).toBeDefined()
    expect(result.networkInfo.adminSubnet).toBe('10.0.0.0')
  })

  it('detects assigned range', () => {
    const rows = [
      makeRow({ ADMIN_IP: '10.0.0.10' }),
      makeRow({ SERVICE_TAG: 'SVC002', ADMIN_IP: '10.0.0.20' }),
    ]
    const result = analyzePxeMapping(rows)
    expect(result.networkInfo.adminAssignedRange).toBe('10.0.0.10-10.0.0.20')
  })

  it('handles single IP for netmask detection', () => {
    const rows = [makeRow({ ADMIN_IP: '10.0.0.10' })]
    const result = analyzePxeMapping(rows)
    expect(result.networkInfo.adminNetmaskBits).toBe(32)
  })
})
