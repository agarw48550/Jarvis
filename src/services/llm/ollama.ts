/**
 * Ollama Local LLM Client
 */

const OLLAMA_API_BASE = 'http://localhost:11434';

export async function chatWithOllama(
    messages: { role: string; content: string }[],
    systemPrompt: string,
    model: string = 'tinyllama:1.1b-chat-v1.0-q4_K_M'
): Promise<string> {
    const response = await fetch(`${OLLAMA_API_BASE}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            model,
            messages: [
                { role: 'system', content: systemPrompt },
                ...messages
            ],
            stream: false,
            options: {
                temperature: 0.7,
                num_predict: 512,
            }
        })
    });

    if (!response.ok) {
        throw new Error(`Ollama error: ${response.statusText}`);
    }

    const data = await response.json();
    return data.message?.content || '';
}

export async function isOllamaRunning(): Promise<boolean> {
    try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 2000);

        const response = await fetch(`${OLLAMA_API_BASE}/api/tags`, {
            signal: controller.signal
        });
        clearTimeout(timeoutId);
        return response.ok;
    } catch {
        return false;
    }
}

export async function listOllamaModels(): Promise<string[]> {
    try {
        const response = await fetch(`${OLLAMA_API_BASE}/api/tags`);
        const data = await response.json();
        return data.models?.map((m: any) => m.name) || [];
    } catch {
        return [];
    }
}
