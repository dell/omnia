import Papa from 'papaparse'

export interface PxeMappingRow {
  FUNCTIONAL_GROUP_NAME: string
  GROUP_NAME: string
  SERVICE_TAG: string
  PARENT_SERVICE_TAG?: string
  HOSTNAME: string
  ADMIN_MAC?: string
  ADMIN_IP?: string
  BMC_MAC?: string
  BMC_IP?: string
  IB_NIC_NAME?: string
  IB_IP?: string
}

const PARSE_CONFIG = {
  header: true as const,
  skipEmptyLines: 'greedy' as const,
  dynamicTyping: false as const,
  transformHeader: (header: string) => header.trim(),
};

const REQUIRED_FIELDS = [
  'FUNCTIONAL_GROUP_NAME',
  'GROUP_NAME',
  'SERVICE_TAG',
  'HOSTNAME',
] as const;

export const ALL_COLUMNS: (keyof PxeMappingRow)[] = [
  'FUNCTIONAL_GROUP_NAME', 'GROUP_NAME', 'SERVICE_TAG', 'PARENT_SERVICE_TAG',
  'HOSTNAME', 'ADMIN_MAC', 'ADMIN_IP', 'BMC_MAC', 'BMC_IP',
  'IB_NIC_NAME', 'IB_IP',
];

function validateHeaders(meta: Papa.ParseMeta): void {
  const missing = REQUIRED_FIELDS.filter((h) => !meta.fields?.includes(h));
  if (missing.length > 0) {
    throw new Error(`CSV is missing required column(s): ${missing.join(', ')}`);
  }
}

export function isValidRow(row: unknown): row is PxeMappingRow {
  const r = row as Record<string, unknown>;
  return REQUIRED_FIELDS.every(
    (field) => typeof r[field] === 'string' && (r[field] as string).length > 0
  );
}

function validateParseResults(results: Papa.ParseResult<PxeMappingRow>): PxeMappingRow[] {
  // Validate headers first
  validateHeaders(results.meta);

  // Filter for truly fatal errors
  const fatalErrors = results.errors.filter(
    (e) => e.type === 'Delimiter' || e.code === 'MissingQuotes'
  );
  if (fatalErrors.length > 0) {
    console.error('CSV parsing errors:', results.errors);
    throw new Error(`CSV parsing failed: ${fatalErrors[0].message}`);
  }

  // Log non-fatal errors as warnings
  const warnings = results.errors.filter((e) => !fatalErrors.includes(e));
  if (warnings.length > 0) {
    console.warn('CSV parsing warnings:', warnings);
  }

  // Validate row shapes at runtime with diagnostic detail
  const invalidEntries = results.data
    .map((row, index) => ({ row, index }))
    .filter(({ row }) => !isValidRow(row));

  if (invalidEntries.length > 0) {
    const details = invalidEntries.slice(0, 5).map(({ row, index }) => {
      const r = row as Partial<PxeMappingRow>;
      const missing = REQUIRED_FIELDS.filter((field) => !r[field]);
      return `Row ${index + 1}: missing [${missing.join(', ')}]`;
    });
    throw new Error(
      `Found ${invalidEntries.length} invalid row(s):\n${details.join('\n')}` +
      (invalidEntries.length > 5 ? `\n...and ${invalidEntries.length - 5} more` : '')
    );
  }

  return results.data;
}

export const parsePxeMappingCsv = (csvString: string): PxeMappingRow[] => {
  const result = Papa.parse<PxeMappingRow>(csvString, PARSE_CONFIG);
  return validateParseResults(result);
}

export const parsePxeMappingFile = (file: File): Promise<PxeMappingRow[]> => {
  return new Promise((resolve, reject) => {
    Papa.parse<PxeMappingRow>(file, {
      ...PARSE_CONFIG,
      complete: (results) => {
        try {
          resolve(validateParseResults(results));
        } catch (error) {
          reject(error);
        }
      },
      error: (error) => {
        reject(error);
      },
    });
  });
}

export const generatePxeMappingCsv = (data: PxeMappingRow[]): string => {
  return Papa.unparse(data, { columns: ALL_COLUMNS });
}

export const downloadPxeMappingCsv = (data: PxeMappingRow[], filename: string = 'pxe_mapping_file.csv') => {
  const csv = generatePxeMappingCsv(data);
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.setAttribute('href', url);
  link.setAttribute('download', filename);
  link.style.visibility = 'hidden';
  document.body.appendChild(link);
  try {
    link.click();
  } finally {
    document.body.removeChild(link);
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
}
