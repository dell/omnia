import { describe, it, expect } from 'vitest'
import { deploymentConfigsSchema } from '../deploymentConfigs'

describe('deploymentConfigsSchema', () => {
  const validAdminNetwork = {
    admin_network: {
      oim_nic_name: 'eth0',
      subnet: '10.0.0.0',
      netmask_bits: '24',
      primary_oim_admin_ip: '10.0.0.1',
      primary_oim_bmc_ip: '',
      dynamic_range: '10.0.0.100-10.0.0.200',
    },
  }

  it('accepts valid admin network', () => {
    const result = deploymentConfigsSchema.safeParse({
      Networks: [validAdminNetwork],
    })
    expect(result.success).toBe(true)
  })

  it('rejects empty Networks array', () => {
    const result = deploymentConfigsSchema.safeParse({ Networks: [] })
    expect(result.success).toBe(false)
  })

  it('rejects missing admin_network', () => {
    const result = deploymentConfigsSchema.safeParse({
      Networks: [{ ib_network: { subnet: '', netmask_bits: '' } }],
    })
    expect(result.success).toBe(false)
  })

  it('rejects invalid subnet IP', () => {
    const result = deploymentConfigsSchema.safeParse({
      Networks: [{
        admin_network: { ...validAdminNetwork.admin_network, subnet: '999.999.999.999' },
      }],
    })
    expect(result.success).toBe(false)
  })

  it('rejects invalid netmask_bits', () => {
    const result = deploymentConfigsSchema.safeParse({
      Networks: [{
        admin_network: { ...validAdminNetwork.admin_network, netmask_bits: '33' },
      }],
    })
    expect(result.success).toBe(false)
  })

  it('rejects missing oim_nic_name', () => {
    const result = deploymentConfigsSchema.safeParse({
      Networks: [{
        admin_network: { ...validAdminNetwork.admin_network, oim_nic_name: '' },
      }],
    })
    expect(result.success).toBe(false)
  })

  it('accepts valid IB network alongside admin', () => {
    const result = deploymentConfigsSchema.safeParse({
      Networks: [
        validAdminNetwork,
        { ib_network: { subnet: '192.168.1.0', netmask_bits: '24' } },
      ],
    })
    expect(result.success).toBe(true)
  })

  it('rejects IB with subnet but no netmask', () => {
    const result = deploymentConfigsSchema.safeParse({
      Networks: [
        validAdminNetwork,
        { ib_network: { subnet: '192.168.1.0', netmask_bits: '' } },
      ],
    })
    expect(result.success).toBe(false)
  })

  it('rejects mismatched admin and IB netmask_bits', () => {
    const result = deploymentConfigsSchema.safeParse({
      Networks: [
        validAdminNetwork,
        { ib_network: { subnet: '192.168.1.0', netmask_bits: '16' } },
      ],
    })
    expect(result.success).toBe(false)
  })
})
