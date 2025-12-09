/**
 * Database Service - TEMPORARILY DISABLED
 */

export function initDatabase(): void {
    console.log('Database disabled');
}

export function getDatabase(): any {
    return null;
}

export const db: any = null;

// Dummy exports for other functions
export function addFact(fact: string, category: string, source: string): any { return 0; }
export function getAllFacts(): any[] { return []; }
export function deleteFact(id: number): void { }
export function saveOAuthTokens(provider: string, accessToken: string, refreshToken: string, expiresAt: Date, scope: string): void { }
export function getOAuthTokens(provider: string): any { return null; }
export function deleteOAuthTokens(provider: string): void { }
export function logAction(action: string, params: any, result: string, success: boolean, confirmed: boolean): void { }
export function getSetting(key: string): any { return null; }
export function setSetting(key: string, value: any): void { }
