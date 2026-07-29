import Papa from 'papaparse'

export interface AdminInventoryRow {
  SERVICE_TAG: string
  GROUP_NAME: string
  FUNCTIONAL_GROUP_NAME: string
  ROW: string
  RACK: string
  SLOT: string
  RANGE: string
}

const PARSE_CONFIG = {
  header: true as const,
  skipEmptyLines: 'greedy' as const,
  dynamicTyping: false as const,
  delimiter: ',' as const,
  transformHeader: (header: string) => {
    const trimmed = header.trim();
    // Normalize BMC_MAC alias to SERVICE_TAG
    if (trimmed === 'BMC_MAC') return 'SERVICE_TAG';
    return trimmed;
  },
};

const REQUIRED_FIELDS = ['SERVICE_TAG'] as const;

export const ADMIN_INVENTORY_COLUMNS: (keyof AdminInventoryRow)[] = [
  'SERVICE_TAG', 'GROUP_NAME', 'FUNCTIONAL_GROUP_NAME',
  'ROW', 'RACK', 'SLOT', 'RANGE',
];

function validateHeaders(meta: Papa.ParseMeta): void {
  const fields = meta.fields || [];
  // Accept SERVICE_TAG or BMC_MAC (already normalized by transformHeader)
  const hasServiceTag = fields.includes('SERVICE_TAG');
  if (!hasServiceTag) {
    throw new Error('CSV is missing required column: SERVICE_TAG (or BMC_MAC)');
  }
}

function isValidRow(row: unknown): row is AdminInventoryRow {
  const r = row as Record<string, unknown>;
  return REQUIRED_FIELDS.every(
    (field) => typeof r[field] === 'string' && (r[field] as string).length > 0
  );
}

function validateParseResults(results: Papa.ParseResult<AdminInventoryRow>): AdminInventoryRow[] {
  validateHeaders(results.meta);

  if (results.data.length === 0) {
    throw new Error('CSV contains no data rows');
  }

  const fatalErrors = results.errors.filter(
    (e) => e.type === 'Delimiter' || e.code === 'MissingQuotes'
  );
  if (fatalErrors.length > 0) {
    console.error('CSV parsing errors:', results.errors);
    throw new Error(`CSV parsing failed: ${fatalErrors[0].message}`);
  }

  const warnings = results.errors.filter((e) => !fatalErrors.includes(e));
  if (warnings.length > 0) {
    console.warn('CSV parsing warnings:', warnings);
  }

  const invalidEntries = results.data
    .map((row, index) => ({ row, index }))
    .filter(({ row }) => !isValidRow(row));

  if (invalidEntries.length > 0) {
    const details = invalidEntries.slice(0, 5).map(({ row, index }) => {
      const r = row as Partial<AdminInventoryRow>;
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

export const parseAdminInventoryFile = (file: File): Promise<AdminInventoryRow[]> => {
  return new Promise((resolve, reject) => {
    Papa.parse<AdminInventoryRow>(file, {
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
