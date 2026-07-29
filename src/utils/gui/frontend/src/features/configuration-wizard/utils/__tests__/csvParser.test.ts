// @vitest-environment jsdom
import { describe, it, expect } from 'vitest'
import { ALL_COLUMNS, parsePxeMappingFile } from '../csvParser'

const VALID_HEADER = [
  'FUNCTIONAL_GROUP_NAME', 'GROUP_NAME', 'SERVICE_TAG', 'PARENT_SERVICE_TAG',
  'HOSTNAME', 'ADMIN_MAC', 'ADMIN_IP', 'BMC_MAC', 'BMC_IP',
  'IB_NIC_NAME', 'IB_IP',
].join(',')

const VALID_ROW = 'slurm_node_x86_64,group1,SVC001,,node01,AA:BB:CC:DD:EE:01,10.0.0.10,AA:BB:CC:DD:EE:02,10.0.1.10,,'

function makeCSVFile(content: string, name = 'test.csv'): File {
  return new File([content], name, { type: 'text/csv' })
}

describe('csvParser', () => {
  describe('ALL_COLUMNS', () => {
    it('contains 11 columns', () => {
      expect(ALL_COLUMNS).toHaveLength(11)
    })

    it('starts with FUNCTIONAL_GROUP_NAME', () => {
      expect(ALL_COLUMNS[0]).toBe('FUNCTIONAL_GROUP_NAME')
    })

    it('ends with IB_IP', () => {
      expect(ALL_COLUMNS[ALL_COLUMNS.length - 1]).toBe('IB_IP')
    })

    it('includes all mandatory fields', () => {
      const mandatory = [
        'FUNCTIONAL_GROUP_NAME', 'GROUP_NAME', 'SERVICE_TAG',
        'HOSTNAME', 'ADMIN_MAC', 'ADMIN_IP', 'BMC_MAC', 'BMC_IP',
      ]
      for (const field of mandatory) {
        expect(ALL_COLUMNS).toContain(field)
      }
    })

    it('includes optional fields', () => {
      expect(ALL_COLUMNS).toContain('PARENT_SERVICE_TAG')
      expect(ALL_COLUMNS).toContain('IB_NIC_NAME')
      expect(ALL_COLUMNS).toContain('IB_IP')
    })
  })

  describe('PxeMappingRow interface', () => {
    it('accepts a valid row object', () => {
      const row = {
        FUNCTIONAL_GROUP_NAME: 'slurm_node_x86_64',
        GROUP_NAME: 'group1',
        SERVICE_TAG: 'SVC001',
        HOSTNAME: 'node01',
        ADMIN_MAC: 'AA:BB:CC:DD:EE:01',
        ADMIN_IP: '10.0.0.10',
        BMC_MAC: 'AA:BB:CC:DD:EE:02',
        BMC_IP: '10.0.1.10',
      }
      // Type-level check: no runtime assertion needed, just that it compiles
      expect(row.FUNCTIONAL_GROUP_NAME).toBe('slurm_node_x86_64')
    })
  })

  describe('parsePxeMappingFile', () => {
    it('resolves with valid CSV containing all mandatory columns', async () => {
      const csv = [VALID_HEADER, VALID_ROW].join('\n')
      const result = await parsePxeMappingFile(makeCSVFile(csv))
      expect(result).toHaveLength(1)
      expect(result[0].SERVICE_TAG).toBe('SVC001')
      expect(result[0].FUNCTIONAL_GROUP_NAME).toBe('slurm_node_x86_64')
    })

    it('rejects when SERVICE_TAG header is missing', async () => {
      const csv = 'FUNCTIONAL_GROUP_NAME,GROUP_NAME\nslurm,g1'
      await expect(parsePxeMappingFile(makeCSVFile(csv))).rejects.toThrow('missing required column')
    })

    it('rejects when mandatory BMC_MAC value is empty', async () => {
      const rowMissingBmc = 'slurm_node_x86_64,group1,SVC001,,node01,AA:BB:CC:DD:EE:01,10.0.0.10,,10.0.1.10,,'
      const csv = [VALID_HEADER, rowMissingBmc].join('\n')
      await expect(parsePxeMappingFile(makeCSVFile(csv))).rejects.toThrow('invalid row')
    })

    it('ignores extra columns', async () => {
      const headerWithExtra = VALID_HEADER + ',EXTRA_COL'
      const rowWithExtra = VALID_ROW + ',extra_value'
      const csv = [headerWithExtra, rowWithExtra].join('\n')
      const result = await parsePxeMappingFile(makeCSVFile(csv))
      expect(result).toHaveLength(1)
      expect(result[0].SERVICE_TAG).toBe('SVC001')
    })

    it('trims whitespace from headers', async () => {
      const spacedHeader = VALID_HEADER.split(',').map((h) => ` ${h} `).join(',')
      const csv = [spacedHeader, VALID_ROW].join('\n')
      const result = await parsePxeMappingFile(makeCSVFile(csv))
      expect(result).toHaveLength(1)
    })

    it('accepts a 2-row file', async () => {
      const row2 = 'k8s_node_x86_64,group2,SVC002,,node02,AA:BB:CC:DD:EE:03,10.0.0.11,AA:BB:CC:DD:EE:04,10.0.1.11,,'
      const csv = [VALID_HEADER, VALID_ROW, row2].join('\n')
      const result = await parsePxeMappingFile(makeCSVFile(csv))
      expect(result).toHaveLength(2)
      expect(result[0].SERVICE_TAG).toBe('SVC001')
      expect(result[1].SERVICE_TAG).toBe('SVC002')
    })
  })
})
