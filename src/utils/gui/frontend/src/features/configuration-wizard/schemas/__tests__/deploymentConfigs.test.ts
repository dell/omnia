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
