/**
 * Google OAuth2 Authentication
 */

import { BrowserWindow } from 'electron';
// Temporary in-memory storage for testing
let tokenStore: Record<string, any> = {};

function saveOAuthTokens(provider: string, accessToken: string, refreshToken: string, expiresAt: Date, scope: string) {
    tokenStore[provider] = { accessToken, refreshToken, expiresAt, scope };
}

function getOAuthTokens(provider: string) {
    return tokenStore[provider] || null;
}

function deleteOAuthTokens(provider: string) {
    delete tokenStore[provider];
}

const GOOGLE_AUTH_URL = 'https://accounts.google.com/o/oauth2/v2/auth';
const GOOGLE_TOKEN_URL = 'https://oauth2.googleapis.com/token';

const SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/calendar.events',
    'https://www.googleapis.com/auth/contacts.readonly',
];

const REDIRECT_URI = 'http://localhost:8234/oauth/callback';

interface GoogleTokens {
    accessToken: string;
    refreshToken: string;
    expiresAt: Date;
}

// Get credentials from environment
function getCredentials() {
    return {
        clientId: process.env.GOOGLE_CLIENT_ID || '',
        clientSecret: process.env.GOOGLE_CLIENT_SECRET || '',
    };
}

export async function startGoogleOAuth(): Promise<GoogleTokens> {
    const { clientId, clientSecret } = getCredentials();

    if (!clientId || !clientSecret) {
        throw new Error('Google OAuth credentials not configured.  Check your .env file.');
    }

    return new Promise((resolve, reject) => {
        // Build auth URL
        const authUrl = new URL(GOOGLE_AUTH_URL);
        authUrl.searchParams.set('client_id', clientId);
        authUrl.searchParams.set('redirect_uri', REDIRECT_URI);
        authUrl.searchParams.set('response_type', 'code');
        authUrl.searchParams.set('scope', SCOPES.join(' '));
        authUrl.searchParams.set('access_type', 'offline');
        authUrl.searchParams.set('prompt', 'consent');

        // Create auth window
        const authWindow = new BrowserWindow({
            width: 600,
            height: 700,
            show: true,
            webPreferences: {
                nodeIntegration: false,
                contextIsolation: true,
            },
            autoHideMenuBar: true,
        });

        authWindow.loadURL(authUrl.toString());

        // Listen for redirect
        authWindow.webContents.on('will-redirect', async (event, url) => {
            if (url.startsWith(REDIRECT_URI)) {
                event.preventDefault();

                const urlObj = new URL(url);
                const code = urlObj.searchParams.get('code');
                const error = urlObj.searchParams.get('error');

                authWindow.close();

                if (error) {
                    reject(new Error(`OAuth error: ${error}`));
                    return;
                }

                if (!code) {
                    reject(new Error('No authorization code received'));
                    return;
                }

                try {
                    const tokens = await exchangeCodeForTokens(code, clientId, clientSecret);

                    // Save tokens to database
                    saveOAuthTokens(
                        'google',
                        tokens.accessToken,
                        tokens.refreshToken,
                        tokens.expiresAt,
                        SCOPES.join(' ')
                    );

                    resolve(tokens);
                } catch (err) {
                    reject(err);
                }
            }
        });

        authWindow.on('closed', () => {
            reject(new Error('Authentication window was closed'));
        });
    });
}

async function exchangeCodeForTokens(
    code: string,
    clientId: string,
    clientSecret: string
): Promise<GoogleTokens> {
    const response = await fetch(GOOGLE_TOKEN_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({
            code,
            client_id: clientId,
            client_secret: clientSecret,
            redirect_uri: REDIRECT_URI,
            grant_type: 'authorization_code',
        }),
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(`Token exchange failed: ${error.error_description || error.error}`);
    }

    const data = await response.json();

    return {
        accessToken: data.access_token,
        refreshToken: data.refresh_token,
        expiresAt: new Date(Date.now() + data.expires_in * 1000),
    };
}

export async function refreshGoogleToken(): Promise<GoogleTokens | null> {
    const { clientId, clientSecret } = getCredentials();
    const stored = getOAuthTokens('google');

    if (!stored?.refreshToken) {
        return null;
    }

    const response = await fetch(GOOGLE_TOKEN_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({
            refresh_token: stored.refreshToken,
            client_id: clientId,
            client_secret: clientSecret,
            grant_type: 'refresh_token',
        }),
    });

    if (!response.ok) {
        // Token invalid, clear it
        deleteOAuthTokens('google');
        return null;
    }

    const data = await response.json();

    const tokens: GoogleTokens = {
        accessToken: data.access_token,
        refreshToken: stored.refreshToken,
        expiresAt: new Date(Date.now() + data.expires_in * 1000),
    };

    saveOAuthTokens('google', tokens.accessToken, tokens.refreshToken, tokens.expiresAt, SCOPES.join(' '));

    return tokens;
}

export async function getValidAccessToken(): Promise<string | null> {
    const stored = getOAuthTokens('google');

    if (!stored) {
        return null;
    }

    // Check if token is expired (with 5 minute buffer)
    if (new Date() >= new Date(stored.expiresAt.getTime() - 5 * 60 * 1000)) {
        const refreshed = await refreshGoogleToken();
        return refreshed?.accessToken || null;
    }

    return stored.accessToken;
}

export function isGoogleConnected(): boolean {
    const tokens = getOAuthTokens('google');
    return tokens !== null;
}

export function disconnectGoogle(): void {
    deleteOAuthTokens('google');
}
