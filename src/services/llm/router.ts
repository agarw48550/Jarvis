/**
 * Smart LLM Router - Gemini → OpenRouter → Ollama
 */

import { chatWithGemini } from './gemini';
import { chatWithOpenRouter, FREE_MODELS } from './openrouter';
import { chatWithOllama, isOllamaRunning } from './ollama';

type TaskType = 'simple' | 'complex' | 'coding' | 'long';

interface LLMConfig {
    geminiKeys: string[];
    openRouterKey: string;
}

// Track Gemini key rotation
let currentGeminiKeyIndex = 0;

// Get API keys from environment
function getConfig(): LLMConfig {
    // In Electron, access via window.electronAPI or process.env
    return {
        geminiKeys: [
            process.env.GEMINI_API_KEY_1 || '',
            process.env.GEMINI_API_KEY_2 || '',
        ].filter(Boolean),
        openRouterKey: process.env.OPENROUTER_API_KEY || '',
    };
}

// Classify task complexity from user message
function classifyTask(message: string): TaskType {
    const lower = message.toLowerCase();

    // Coding indicators
    if (/\b(code|program|function|debug|script|api|implement|build|create.*app|javascript|python|typescript)\b/.test(lower)) {
        return 'coding';
    }

    // Long document indicators
    if (message.length > 1000 || /\b(document|article|essay|summary|analyze.*long)\b/.test(lower)) {
        return 'long';
    }

    // Complex reasoning indicators
    if (/\b(explain|analyze|compare|why|how does|research|detailed|comprehensive|strategy|plan|step.by.step)\b/.test(lower)) {
        return 'complex';
    }

    return 'simple';
}

// Check internet connectivity
async function checkConnectivity(): Promise<boolean> {
    try {
        const controller = new AbortController();
        setTimeout(() => controller.abort(), 3000);

        await fetch('https://www.google.com/favicon.ico', {
            mode: 'no-cors',
            signal: controller.signal
        });
        return true;
    } catch {
        return false;
    }
}

export async function routeToLLM(
    messages: { role: string; content: string }[],
    systemPrompt: string
): Promise<string> {
    const config = getConfig();
    const lastMessage = messages[messages.length - 1]?.content || '';
    const taskType = classifyTask(lastMessage);

    console.log(`🧠 Task type: ${taskType}`);

    // Check connectivity
    const isOnline = await checkConnectivity();

    if (!isOnline) {
        console.log('📴 Offline mode - using Ollama');
        return tryOllama(messages, systemPrompt);
    }

    // Try Gemini first
    if (config.geminiKeys.length > 0) {
        const geminiModel = taskType === 'simple' ? 'gemini-2.5-flash' : 'gemini-2.5-pro';

        for (let i = 0; i < config.geminiKeys.length; i++) {
            const keyIndex = (currentGeminiKeyIndex + i) % config.geminiKeys.length;
            const apiKey = config.geminiKeys[keyIndex];

            try {
                console.log(`🔷 Trying Gemini ${geminiModel} (key ${keyIndex + 1})`);
                const response = await chatWithGemini(messages, systemPrompt, {
                    apiKey,
                    model: geminiModel
                });
                return response;
            } catch (error) {
                console.log(`⚠️ Gemini key ${keyIndex + 1} failed: `, error);
                currentGeminiKeyIndex = (keyIndex + 1) % config.geminiKeys.length;
            }
        }
    }

    // Try OpenRouter free models
    if (config.openRouterKey) {
        const modelsToTry = getModelsForTask(taskType);

        for (const model of modelsToTry) {
            try {
                console.log(`🔶 Trying OpenRouter:  ${model}`);
                const response = await chatWithOpenRouter(
                    messages,
                    systemPrompt,
                    model,
                    config.openRouterKey
                );
                return response;
            } catch (error) {
                console.log(`⚠️ OpenRouter ${model} failed:`, error);
            }
        }
    }

    // Final fallback:  Ollama
    return tryOllama(messages, systemPrompt);
}

function getModelsForTask(taskType: TaskType): string[] {
    switch (taskType) {
        case 'coding':
            return [...FREE_MODELS.coding, ...FREE_MODELS.reasoning];
        case 'complex':
            return FREE_MODELS.reasoning;
        case 'long':
            return FREE_MODELS.longContext;
        default:
            return FREE_MODELS.conversation;
    }
}

async function tryOllama(
    messages: { role: string; content: string }[],
    systemPrompt: string
): Promise<string> {
    const ollamaAvailable = await isOllamaRunning();

    if (!ollamaAvailable) {
        throw new Error(
            'No LLM available.  Please ensure:\n' +
            '1. You have valid API keys in your .env file, OR\n' +
            '2. Ollama is running (ollama serve)'
        );
    }

    console.log('🟢 Using Ollama (local)');
    return chatWithOllama(messages, systemPrompt);
}
