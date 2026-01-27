// Currency and number formatting utilities

/**
 * Format a number as currency using the provided locale and currency code.
 * Falls back to USD and en-US if not specified.
 */
export function formatCurrency(
    value: number | string,
    currency: string = "USD",
    locale: string = "en-US"
): string {
    const numValue = typeof value === "string" ? parseFloat(value) : value;

    if (isNaN(numValue)) {
        return "$0.00";
    }

    try {
        return new Intl.NumberFormat(locale, {
            style: "currency",
            currency,
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        }).format(numValue);
    } catch {
        // Fallback if locale/currency is invalid
        return `$${numValue.toFixed(2)}`;
    }
}

/**
 * Format a number with thousand separators.
 */
export function formatNumber(
    value: number | string,
    locale: string = "en-US",
    decimals: number = 2
): string {
    const numValue = typeof value === "string" ? parseFloat(value) : value;

    if (isNaN(numValue)) {
        return "0";
    }

    try {
        return new Intl.NumberFormat(locale, {
            minimumFractionDigits: decimals,
            maximumFractionDigits: decimals,
        }).format(numValue);
    } catch {
        return numValue.toFixed(decimals);
    }
}

/**
 * Format a percentage value.
 */
export function formatPercent(
    value: number | string,
    locale: string = "en-US",
    decimals: number = 2
): string {
    const numValue = typeof value === "string" ? parseFloat(value) : value;

    if (isNaN(numValue)) {
        return "0%";
    }

    try {
        return new Intl.NumberFormat(locale, {
            style: "percent",
            minimumFractionDigits: decimals,
            maximumFractionDigits: decimals,
        }).format(numValue / 100);
    } catch {
        return `${numValue.toFixed(decimals)}%`;
    }
}

/**
 * Get UTC date string to avoid timezone issues with backend.
 */
export function getUTCDateString(): string {
    const now = new Date();
    const year = now.getUTCFullYear();
    const month = String(now.getUTCMonth() + 1).padStart(2, "0");
    const day = String(now.getUTCDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
}
