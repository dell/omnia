const SECTION_LABELS: Record<string, string> = {
    FunctionalPackages: 'Package',
    OSPackages: 'Package',
    InfrastructurePackages: 'Package',
    FunctionalLayer: 'Layer',
    BaseOS: 'BaseOS',
    DriverPackages: 'Driver package',
    Drivers: 'Driver',
    Miscellaneous: 'Miscellaneous item',
};

interface ApiError {
    data?: {
        details?: Array<{ loc?: string[]; msg?: string }>;
        detail?: string | Array<{ loc?: string[]; msg?: string }>;
        error?: string;
    };
    response?: { data?: { detail?: string | Array<{ loc?: string[]; msg?: string }> } };
    message?: string;
}

export function extractErrorMessage(err: ApiError | any): string {
    const details =
        err?.data?.details ?? err?.data?.detail ?? err?.response?.data?.detail;

    if (Array.isArray(details)) {
        return details
            .map((d: any) => {
                const loc = d.loc?.join('.') ?? '';
                return `${loc} - ${d.msg ?? 'Unknown error'}`;
            })
            .join('; ');
    }

    return err?.data?.error ?? err?.message ?? 'Unknown error';
}

export function extractUserFriendlyErrorMessage(err: ApiError | any): string {
    const details = err?.data?.details;

    if (Array.isArray(details)) {
        return details
            .map((d: any) => {
                const loc: string[] = d.loc || [];
                const msg = d.msg || 'Unknown error';

                if (loc.length >= 5 && loc[0] === 'body' && loc[1] === 'Catalog') {
                    const section = loc[2];
                    const itemId = loc[3];
                    const field = loc[4];
                    const label = SECTION_LABELS[section];

                    if (label) {
                        return `${label} '${itemId}', field '${field}': ${msg}`;
                    }
                }

                return `${loc.join('.')} - ${msg}`;
            })
            .join('; ');
    }

    return extractErrorMessage(err);
}
