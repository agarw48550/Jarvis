/**
 * Web Search Actions - Using DuckDuckGo
 */

import { ActionResult } from './index';

export async function handleSearchWeb(params: {
    query: string;
}): Promise<ActionResult> {
    try {
        // Use DuckDuckGo Instant Answer API (free, no key needed)
        const query = encodeURIComponent(params.query);
        const response = await fetch(
            `https://api.duckduckgo.com/?q=${query}&format=json&no_html=1&skip_disambig=1`
        );

        if (!response.ok) {
            throw new Error('Search failed');
        }

        const data = await response.json();

        // Try to get an instant answer
        if (data.AbstractText) {
            return {
                success: true,
                message: data.AbstractText,
                data: {
                    source: data.AbstractSource,
                    url: data.AbstractURL,
                },
            };
        }

        // Try related topics
        if (data.RelatedTopics?.length > 0) {
            const topics = data.RelatedTopics
                .filter((t: any) => t.Text)
                .slice(0, 3)
                .map((t: any) => t.Text);

            if (topics.length > 0) {
                return {
                    success: true,
                    message: `Here's what I found: ${topics.join(' ')}`,
                    data: { topics },
                };
            }
        }

        // Fallback message
        return {
            success: true,
            message: `I searched for "${params.query}" but couldn't find a quick answer.  You might want to search the web directly for more detailed results.`,
        };
    } catch (error) {
        return {
            success: false,
            message: `Search failed: ${error}`,
        };
    }
}
