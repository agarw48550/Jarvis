/**
 * Email Actions - Gmail Integration
 */

import { getValidAccessToken } from '../auth/google';
import { ActionResult } from './index';

const GMAIL_API_BASE = 'https://gmail.googleapis.com/gmail/v1';

export async function handleSendEmail(params: {
    to: string;
    subject: string;
    body: string;
}): Promise<ActionResult> {
    const accessToken = await getValidAccessToken();

    if (!accessToken) {
        return {
            success: false,
            message: 'Gmail not connected. Please connect your Google account first.',
        };
    }

    try {
        // Create email in RFC 2822 format
        const email = [
            `To: ${params.to}`,
            `Subject: ${params.subject}`,
            'Content-Type: text/plain; charset=utf-8',
            '',
            params.body,
        ].join('\r\n');

        // Base64 URL encode
        const encodedEmail = Buffer.from(email)
            .toString('base64')
            .replace(/\+/g, '-')
            .replace(/\//g, '_')
            .replace(/=+$/, '');

        const response = await fetch(`${GMAIL_API_BASE}/users/me/messages/send`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${accessToken}`,
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ raw: encodedEmail }),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error?.message || 'Failed to send email');
        }

        return {
            success: true,
            message: `Email sent to ${params.to}!`,
        };
    } catch (error) {
        return {
            success: false,
            message: `Failed to send email: ${error}`,
        };
    }
}

export async function handleReadEmails(params: {
    query?: string;
    maxResults?: number;
}): Promise<ActionResult> {
    const accessToken = await getValidAccessToken();

    if (!accessToken) {
        return {
            success: false,
            message: 'Gmail not connected.  Please connect your Google account first.',
        };
    }

    try {
        const query = params.query || 'is:unread';
        const maxResults = params.maxResults || 5;

        // Get message list
        const listResponse = await fetch(
            `${GMAIL_API_BASE}/users/me/messages?q=${encodeURIComponent(query)}&maxResults=${maxResults}`,
            {
                headers: { 'Authorization': `Bearer ${accessToken}` },
            }
        );

        if (!listResponse.ok) {
            throw new Error('Failed to fetch emails');
        }

        const listData = await listResponse.json();
        const messages = listData.messages || [];

        if (messages.length === 0) {
            return {
                success: true,
                message: 'No emails found matching your query.',
                data: [],
            };
        }

        // Fetch email details
        const emailDetails = await Promise.all(
            messages.slice(0, maxResults).map(async (msg: any) => {
                const detailResponse = await fetch(
                    `${GMAIL_API_BASE}/users/me/messages/${msg.id}?format=metadata&metadataHeaders=Subject&metadataHeaders=From&metadataHeaders=Date`,
                    {
                        headers: { 'Authorization': `Bearer ${accessToken}` },
                    }
                );
                return detailResponse.json();
            })
        );

        const emails = emailDetails.map((email: any) => {
            const headers = email.payload?.headers || [];
            return {
                id: email.id,
                subject: headers.find((h: any) => h.name === 'Subject')?.value || 'No Subject',
                from: headers.find((h: any) => h.name === 'From')?.value || 'Unknown',
                date: headers.find((h: any) => h.name === 'Date')?.value || '',
                snippet: email.snippet,
            };
        });

        const summary = emails.map((e, i) =>
            `${i + 1}.  From ${e.from.split('<')[0].trim()}: "${e.subject}"`
        ).join('.  ');

        return {
            success: true,
            message: `You have ${emails.length} emails.  ${summary}`,
            data: emails,
        };
    } catch (error) {
        return {
            success: false,
            message: `Failed to read emails: ${error}`,
        };
    }
}
