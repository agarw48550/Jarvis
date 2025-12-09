/**
 * Action Registry and Executor
 */

// import { logAction } from '../database';
const logAction = (a: any, b: any, c: any, d: any, e: any) => { }; // Dummy
import { handleSendEmail, handleReadEmails } from './email';
import { handleCreateCalendarEvent, handleGetCalendarEvents } from './calendar';
import { handleGetWeather } from './weather';
import { handleSearchWeb } from './search';
import { handleOpenApp } from './system';
import { handleReadFile, handleWriteFile } from './files';
import { handleSaveFact } from './memory';

export interface ActionResult {
    success: boolean;
    message: string;
    data?: any;
}

export type DangerLevel = 'low' | 'medium' | 'high' | 'critical';

export interface ActionDefinition {
    name: string;
    description: string;
    dangerLevel: DangerLevel;
    handler: (params: Record<string, any>) => Promise<ActionResult>;
}

// Danger levels determine if voice confirmation is needed
const DANGER_LEVELS: Record<string, DangerLevel> = {
    SAVE_FACT: 'low',
    SEARCH_WEB: 'low',
    GET_WEATHER: 'low',
    OPEN_APP: 'low',
    READ_FILE: 'medium',
    CREATE_CALENDAR_EVENT: 'medium',
    SET_REMINDER: 'medium',
    PLAY_MUSIC: 'low',
    SEND_EMAIL: 'high',
    SEND_MESSAGE: 'high',
    WRITE_FILE: 'high',
    DELETE_FILE: 'critical',
};

export function getDangerLevel(actionName: string): DangerLevel {
    return DANGER_LEVELS[actionName] || 'medium';
}

export function needsConfirmation(actionName: string): boolean {
    const level = getDangerLevel(actionName);
    return level === 'high' || level === 'critical';
}

export async function generateConfirmationMessage(
    actionName: string,
    params: Record<string, any>
): Promise<string> {
    switch (actionName) {
        case 'SEND_EMAIL':
            return `I'm about to send an email to ${params.to} with the subject "${params.subject}". ` +
                `The message says:  "${params.body?.substring(0, 100)}${params.body?.length > 100 ? '...' : ''}".  ` +
                `Should I send it? Say yes or no.`;

        case 'SEND_MESSAGE':
            return `I'll send a ${params.platform} message to ${params.to} saying:  "${params.message}".  ` +
                `Is that okay? Say yes or no.`;

        case 'WRITE_FILE':
            return `I'm going to write to the file at ${params.path}. Should I proceed? Say yes or no.`;

        case 'DELETE_FILE':
            return `Warning: I'm about to permanently delete the file at ${params.path}.  ` +
                `This cannot be undone.  Are you absolutely sure? Say yes to confirm or no to cancel.`;

        case 'CREATE_CALENDAR_EVENT':
            return `I'll create a calendar event called "${params.title}" for ${params.datetime}. ` +
                `Should I add it?  Say yes or no. `;

        default:
            return `I'm about to perform ${actionName}. Should I continue? Say yes or no.`;
    }
}

export async function executeActionWithConfirmation(
    actionName: string,
    params: Record<string, any>,
    voiceInterface: {
        speak: (text: string) => Promise<void>;
        listenForYesNo: () => Promise<boolean>;
    }
): Promise<ActionResult> {
    const needsVoiceConfirmation = needsConfirmation(actionName);

    if (needsVoiceConfirmation) {
        const confirmMessage = await generateConfirmationMessage(actionName, params);
        await voiceInterface.speak(confirmMessage);

        const confirmed = await voiceInterface.listenForYesNo();

        if (!confirmed) {
            logAction(actionName, params, 'Cancelled by user', false, false);
            return {
                success: false,
                message: 'Action cancelled.',
            };
        }
    }

    // Execute the action
    const handler = actionHandlers[actionName];

    if (!handler) {
        return {
            success: false,
            message: `Unknown action: ${actionName}`,
        };
    }

    try {
        const result = await handler(params);
        logAction(actionName, params, result.message, result.success, needsVoiceConfirmation);
        return result;
    } catch (error) {
        const errorMessage = error instanceof Error ? error.message : String(error);
        logAction(actionName, params, errorMessage, false, needsVoiceConfirmation);
        return {
            success: false,
            message: `Action failed: ${errorMessage}`,
        };
    }
}

export const actionHandlers: Record<string, (params: any) => Promise<ActionResult>> = {
    SAVE_FACT: handleSaveFact,
    SEND_EMAIL: handleSendEmail,
    READ_EMAILS: handleReadEmails,
    CREATE_CALENDAR_EVENT: handleCreateCalendarEvent,
    GET_CALENDAR_EVENTS: handleGetCalendarEvents,
    GET_WEATHER: handleGetWeather,
    SEARCH_WEB: handleSearchWeb,
    OPEN_APP: handleOpenApp,
    READ_FILE: handleReadFile,
    WRITE_FILE: handleWriteFile,
};
