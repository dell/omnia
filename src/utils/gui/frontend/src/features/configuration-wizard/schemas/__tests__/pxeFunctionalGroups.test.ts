import { describe, it, expect } from 'vitest'
import { pxeFunctionalGroupsSchema } from '../pxeFunctionalGroups'

describe('pxeFunctionalGroupsSchema', () => {
  const validRow = {
    FUNCTIONAL_GROUP_NAME: 'slurm_node_x86_64',
    GROUP_NAME: 'group1',
    SERVICE_TAG: 'SVC001',
    PARENT_SERVICE_TAG: '',
    HOSTNAME: 'node01',
    ADMIN_MAC: 'AA:BB:CC:DD:EE:01',
    ADMIN_IP: '10.0.0.10',
    BMC_MAC: 'AA:BB:CC:DD:EE:02',
    BMC_IP: '10.0.1.10',
  }

  const validData = {
    pxe_mapping_file_path: '/opt/omnia/input/pxe_mapping_file.csv',
    pxe_mapping_data: [validRow],
    default_lease_time: '86400',
  }

  it('accepts valid data', () => {
    const result = pxeFunctionalGroupsSchema.safeParse(validData)
    expect(result.success).toBe(true)
  })

  it('rejects invalid functional group name format', () => {
    const result = pxeFunctionalGroupsSchema.safeParse({
      ...validData,
      pxe_mapping_data: [{ ...validRow, FUNCTIONAL_GROUP_NAME: 'invalid_name' }],
    })
    expect(result.success).toBe(false)
  })

  it('rejects functional group name starting with number', () => {
    const result = pxeFunctionalGroupsSchema.safeParse({
      ...validData,
      pxe_mapping_data: [{ ...validRow, FUNCTIONAL_GROUP_NAME: '1_bad_x86_64' }],
    })
    expect(result.success).toBe(false)
  })

  it('rejects empty pxe_mapping_file_path', () => {
    const result = pxeFunctionalGroupsSchema.safeParse({
      ...validData,
      pxe_mapping_file_path: '',
    })
    expect(result.success).toBe(false)
  })

  it('rejects empty pxe_mapping_data', () => {
    const result = pxeFunctionalGroupsSchema.safeParse({
      ...validData,
      pxe_mapping_data: [],
    })
    expect(result.success).toBe(false)
  })

  it('rejects missing GROUP_NAME', () => {
    const result = pxeFunctionalGroupsSchema.safeParse({
      ...validData,
      pxe_mapping_data: [{ ...validRow, GROUP_NAME: '' }],
    })
    expect(result.success).toBe(false)
  })

  it('rejects missing SERVICE_TAG', () => {
    const result = pxeFunctionalGroupsSchema.safeParse({
      ...validData,
      pxe_mapping_data: [{ ...validRow, SERVICE_TAG: '' }],
    })
    expect(result.success).toBe(false)
  })

  it('rejects missing HOSTNAME', () => {
    const result = pxeFunctionalGroupsSchema.safeParse({
      ...validData,
      pxe_mapping_data: [{ ...validRow, HOSTNAME: '' }],
    })
    expect(result.success).toBe(false)
  })

  it('rejects missing ADMIN_MAC', () => {
    const result = pxeFunctionalGroupsSchema.safeParse({
      ...validData,
      pxe_mapping_data: [{ ...validRow, ADMIN_MAC: '' }],
    })
    expect(result.success).toBe(false)
  })

  it('rejects missing BMC_MAC', () => {
    const result = pxeFunctionalGroupsSchema.safeParse({
      ...validData,
      pxe_mapping_data: [{ ...validRow, BMC_MAC: '' }],
    })
    expect(result.success).toBe(false)
  })

  it('rejects lease time below minimum', () => {
    const result = pxeFunctionalGroupsSchema.safeParse({
      ...validData,
      default_lease_time: '100',
    })
    expect(result.success).toBe(false)
  })

  it('rejects lease time above maximum', () => {
    const result = pxeFunctionalGroupsSchema.safeParse({
      ...validData,
      default_lease_time: '99999999',
    })
    expect(result.success).toBe(false)
  })

  it('accepts valid cloud init file path', () => {
    const result = pxeFunctionalGroupsSchema.safeParse({
      ...validData,
      additional_cloud_init_config_file: '/path/to/cloud_init.yml',
    })
    expect(result.success).toBe(true)
  })

  it('rejects cloud init file without yml/yaml extension', () => {
    const result = pxeFunctionalGroupsSchema.safeParse({
      ...validData,
      additional_cloud_init_config_file: '/path/to/config.json',
    })
    expect(result.success).toBe(false)
  })
})
