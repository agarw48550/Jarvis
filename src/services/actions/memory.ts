/**
 * Memory Actions - Save and recall user facts
 */

// import { addFact, getAllFacts, deleteFact } from '../database';
import { ActionResult } from './index';

let mockFacts: any[] = [];

export async function handleSaveFact(params: {
    fact: string;
    category?: string;
}): Promise<ActionResult> {
    try {
        const id = Date.now();
        mockFacts.push({ id, fact: params.fact, category: params.category || 'general' });

        return {
            success: true,
            message: `I'll remember that. `,
            data: { id, fact: params.fact },
        };
    } catch (error) {
        return {
            success: false,
            message: `Couldn't save that:  ${error}`,
        };
    }
}

export async function handleRecallFacts(params: {
    category?: string;
}): Promise<ActionResult> {
    try {
        const facts = mockFacts;

        if (facts.length === 0) {
            return {
                success: true,
                message: "I don't have any saved information about you yet.",
                data: { facts: [] },
            };
        }

        const summary = facts.slice(0, 5).map(f => f.fact).join('.  ');

        return {
            success: true,
            message: `Here's what I know:  ${summary}`,
            data: { facts },
        };
    } catch (error) {
        return {
            success: false,
            message: `Couldn't recall facts: ${error}`,
        };
    }
}

export async function handleForgetFact(params: {
    id?: number;
    all?: boolean;
}): Promise<ActionResult> {
    try {
        if (params.all) {
            mockFacts = [];
            return {
                success: true,
                message: "I've forgotten everything about you.",
            };
        }

        if (params.id) {
            mockFacts = mockFacts.filter(f => f.id !== params.id);
            return {
                success: true,
                message: "I've forgotten that.",
            };
        }

        return {
            success: false,
            message: "Please specify what to forget.",
        };
    } catch (error) {
        return {
            success: false,
            message: `Couldn't forget:  ${error}`,
        };
    }
}
