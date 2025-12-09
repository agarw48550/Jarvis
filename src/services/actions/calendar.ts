/**
 * Calendar Actions - Google Calendar Integration
 */

import { getValidAccessToken } from '../auth/google';
import { ActionResult } from './index';

const CALENDAR_API_BASE = 'https://www.googleapis.com/calendar/v3';

export async function handleCreateCalendarEvent(params: {
    title: string;
    datetime: string;
    duration?: number; // minutes
    description?: string;
    location?: string;
}): Promise<ActionResult> {
    const accessToken = await getValidAccessToken();

    if (!accessToken) {
        return {
            success: false,
            message: 'Calendar not connected. Please connect your Google account first.',
        };
    }

    try {
        const startTime = new Date(params.datetime);
        const endTime = new Date(startTime.getTime() + (params.duration || 60) * 60 * 1000);

        const event = {
            summary: params.title,
            description: params.description || '',
            location: params.location || '',
            start: {
                dateTime: startTime.toISOString(),
                timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone,
            },
            end: {
                dateTime: endTime.toISOString(),
                timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone,
            },
        };

        const response = await fetch(`${CALENDAR_API_BASE}/calendars/primary/events`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${accessToken}`,
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(event),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error?.message || 'Failed to create event');
        }

        const createdEvent = await response.json();

        return {
            success: true,
            message: `Created event "${params.title}" for ${startTime.toLocaleDateString()} at ${startTime.toLocaleTimeString()}.`,
            data: createdEvent,
        };
    } catch (error) {
        return {
            success: false,
            message: `Failed to create event: ${error}`,
        };
    }
}

export async function handleGetCalendarEvents(params: {
    date?: string;
    days?: number;
}): Promise<ActionResult> {
    const accessToken = await getValidAccessToken();

    if (!accessToken) {
        return {
            success: false,
            message: 'Calendar not connected. Please connect your Google account first.',
        };
    }

    try {
        const startDate = params.date ? new Date(params.date) : new Date();
        startDate.setHours(0, 0, 0, 0);

        const endDate = new Date(startDate);
        endDate.setDate(endDate.getDate() + (params.days || 7));

        const response = await fetch(
            `${CALENDAR_API_BASE}/calendars/primary/events?` +
            `timeMin=${startDate.toISOString()}&` +
            `timeMax=${endDate.toISOString()}&` +
            `singleEvents=true&orderBy=startTime&maxResults=20`,
            {
                headers: { 'Authorization': `Bearer ${accessToken}` },
            }
        );

        if (!response.ok) {
            throw new Error('Failed to fetch calendar events');
        }

        const data = await response.json();
        const events = data.items || [];

        if (events.length === 0) {
            return {
                success: true,
                message: 'You have no upcoming events.',
                data: [],
            };
        }

        const eventList = events.map((event: any) => ({
            title: event.summary,
            start: event.start?.dateTime || event.start?.date,
            location: event.location,
        }));

        const summary = eventList.slice(0, 5).map((e: any, i: number) => {
            const date = new Date(e.start);
            return `${i + 1}. "${e.title}" on ${date.toLocaleDateString()} at ${date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
        }).join('. ');

        return {
            success: true,
            message: `You have ${events.length} events coming up.  ${summary}`,
            data: eventList,
        };
    } catch (error) {
        return {
            success: false,
            message: `Failed to get events: ${error}`,
        };
    }
}
