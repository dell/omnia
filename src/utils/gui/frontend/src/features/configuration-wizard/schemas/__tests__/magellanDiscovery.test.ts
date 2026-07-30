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
