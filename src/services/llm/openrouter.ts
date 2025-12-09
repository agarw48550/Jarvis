/**
 * OpenRouter API Client - Free Model Access
 */

const OPENROUTER_API_BASE = 'https://openrouter.ai/api/v1';

// Free models in priority order by use case
export const FREE_MODELS = {
    conversation: [
        'google/gemini-2.0-flash-exp:free',
        'meta-llama/llama-3.3-70b-instruct:free',
        'qwen/qwen3-235b-a22b:free',
        'mistralai/mistral-small-3.1-24b-instruct:free',
        'google/gemma-3-27b-it:free',
    ],
    reasoning: [
        'nousresearch/hermes-3-llama-3.1-405b:free',
        'tngtech/deepseek-r1t-chimera:free',
        'allenai/olmo-3-32b-think:free',
    ],
    coding: [
        'qwen/qwen3-coder:free',
        'kwaipilot/kat-coder-pro:free',
    ],
    longContext: [
        'amazon/nova-2-lite-v1:free',
        'meituan/longcat-flash-chat:free',
    ]
};

export async function chatWithOpenRouter(
    messages: { role: string; content: string }[],
    systemPrompt: string,
    model: string,
    apiKey: string
): Promise<string> {
    if (!apiKey) {
        throw new Error('OpenRouter API key not configured');
    }

    const response = await fetch(`${OPENROUTER_API_BASE}/chat/completions`, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${apiKey}`,
            'Content-Type': 'application/json',
            'HTTP-Referer': 'https://jarvis-assistant.local',
            'X-Title': 'Jarvis AI Assistant',
        },
        body: JSON.stringify({
            model,
            messages: [
                { role: 'system', content: systemPrompt },
                ...messages
            ],
            temperature: 0.7,
            max_tokens: 2048,
        })
    });

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(`OpenRouter error: ${errorData.error?.message || response.statusText}`);
    }

    const data = await response.json();
    return data.choices?.[0]?.message?.content || '';
}
