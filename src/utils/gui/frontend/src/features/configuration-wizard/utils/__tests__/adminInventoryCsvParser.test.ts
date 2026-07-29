// @vitest-environment jsdom
import { describe, it, expect } from 'vitest'
import { ADMIN_INVENTORY_COLUMNS, parseAdminInventoryFile } from '../adminInventoryCsvParser'

const VALID_HEADER = 'SERVICE_TAG,GROUP_NAME,FUNCTIONAL_GROUP_NAME,ROW,RACK,SLOT,RANGE'
const VALID_ROW = 'SVC001,group1,compute,R1,A1,1,'

function makeCSVFile(content: string): File {
  return new File([content], 'test.csv', { type: 'text/csv' })
}

describe('adminInventoryCsvParser', () => {
  describe('ADMIN_INVENTORY_COLUMNS', () => {
    it('contains 7 columns', () => {
      expect(ADMIN_INVENTORY_COLUMNS).toHaveLength(7)
    })

    it('starts with SERVICE_TAG', () => {
      expect(ADMIN_INVENTORY_COLUMNS[0]).toBe('SERVICE_TAG')
    })

    it('ends with RANGE', () => {
      expect(ADMIN_INVENTORY_COLUMNS[ADMIN_INVENTORY_COLUMNS.length - 1]).toBe('RANGE')
    })

    it('includes all expected columns', () => {
      const expected = [
        'SERVICE_TAG', 'GROUP_NAME', 'FUNCTIONAL_GROUP_NAME',
        'ROW', 'RACK', 'SLOT', 'RANGE',
      ]
      for (const col of expected) {
        expect(ADMIN_INVENTORY_COLUMNS).toContain(col)
      }
    })
  })

  describe('AdminInventoryRow interface', () => {
    it('accepts a valid row object', () => {
      const row = {
        SERVICE_TAG: 'SVC001',
        GROUP_NAME: 'group1',
        FUNCTIONAL_GROUP_NAME: 'compute',
        ROW: 'R1',
        RACK: 'A1',
        SLOT: '1',
        RANGE: '',
      }
      expect(row.SERVICE_TAG).toBe('SVC001')
    })
  })

  describe('parseAdminInventoryFile', () => {
    it('resolves with valid CSV', async () => {
      const csv = [VALID_HEADER, VALID_ROW].join('\n')
      const result = await parseAdminInventoryFile(makeCSVFile(csv))
      expect(result).toHaveLength(1)
      expect(result[0].SERVICE_TAG).toBe('SVC001')
      expect(result[0].RANGE).toBe('')
    })

    it('aliases BMC_MAC header to SERVICE_TAG', async () => {
      const csv = ['BMC_MAC,GROUP_NAME', 'AA:BB:CC:DD:EE:01,g1'].join('\n')
      const result = await parseAdminInventoryFile(makeCSVFile(csv))
      expect(result).toHaveLength(1)
      expect(result[0].SERVICE_TAG).toBe('AA:BB:CC:DD:EE:01')
    })

    it('rejects when SERVICE_TAG is missing', async () => {
      const csv = 'GROUP_NAME,RACK\ngroup1,A1'
      await expect(parseAdminInventoryFile(makeCSVFile(csv))).rejects.toThrow('missing required column')
    })

    it('rejects header-only CSV (0 valid rows)', async () => {
      await expect(parseAdminInventoryFile(makeCSVFile(VALID_HEADER))).rejects.toThrow('no data rows')
    })

    it('accepts rows with missing optional columns', async () => {
      const csv = 'SERVICE_TAG\nSVC001'
      const result = await parseAdminInventoryFile(makeCSVFile(csv))
      expect(result).toHaveLength(1)
      expect(result[0].SERVICE_TAG).toBe('SVC001')
      expect(result[0].GROUP_NAME).toBeUndefined()
    })
  })
})
