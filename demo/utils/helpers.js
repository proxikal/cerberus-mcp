/**
 * Formats a date string.
 */
export function formatDate(date) {
    return date.toISOString();
}

/**
 * Generates a random unique ID.
 */
export function generateId() {
    return Math.random().toString(36).substr(2, 9);
}
