import { describe, it, expect } from 'vitest'
import { magellanDiscoverySchema } from '../magellanDiscovery'

describe('magellanDiscoverySchema', () => {
  const validData = {
    admin_inventory_path: '/opt/omnia/input/project_default/admin_inventory.csv',
    admin_inventory_data: [
      {
        SERVICE_TAG: 'SVC001',
        GROUP_NAME: 'group1',
        FUNCTIONAL_GROUP_NAME: 'compute',
        ROW: 'R1',
        RACK: 'A1',
        SLOT: '1',
        RANGE: '',
      },
    ],
  }

  it('accepts valid data', () => {
    const result = magellanDiscoverySchema.safeParse(validData)
    expect(result.success).toBe(true)
  })

  it('rejects empty admin_inventory_path', () => {
    const result = magellanDiscoverySchema.safeParse({
      ...validData,
      admin_inventory_path: '',
    })
    expect(result.success).toBe(false)
  })

  it('rejects empty admin_inventory_data', () => {
    const result = magellanDiscoverySchema.safeParse({
      ...validData,
      admin_inventory_data: [],
    })
    expect(result.success).toBe(false)
  })

  it('rejects missing SERVICE_TAG', () => {
    const result = magellanDiscoverySchema.safeParse({
      ...validData,
      admin_inventory_data: [
        { SERVICE_TAG: '', GROUP_NAME: '', FUNCTIONAL_GROUP_NAME: '' },
      ],
    })
    expect(result.success).toBe(false)
  })

  it('defaults optional fields', () => {
    const result = magellanDiscoverySchema.safeParse({
      admin_inventory_path: '/path',
      admin_inventory_data: [{ SERVICE_TAG: 'SVC001' }],
    })
    expect(result.success).toBe(true)
    if (result.success) {
      const row = result.data.admin_inventory_data[0]
      expect(row.GROUP_NAME).toBe('')
      expect(row.ROW).toBe('')
    }
  })
})
