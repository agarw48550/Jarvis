// jarvis/src/hooks/useVoicePipeline.ts
/**
 * Voice Pipeline Hook - Complete Integration (FIXED)
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { create } from 'zustand';

// Types
export type PipelineState = 'idle' | 'listening' | 'processing' | 'thinking' | 'speaking' | 'error';

interface Message {
    role: 'user' | 'assistant';
    content: string;
    timestamp: Date;
}

interface VoicePipelineStore {
    state: PipelineState;
    isOnline: boolean;
    error: string | null;
    messages: Message[];
    currentTranscript: string;
    currentResponse: string;
    selectedVoice: 'male' | 'female';
    userFacts: string[];

    setState: (state: PipelineState) => void;
    setIsOnline: (online: boolean) => void;
    setError: (error: string | null) => void;
    addMessage: (message: Message) => void;
    setCurrentTranscript: (text: string) => void;
    setCurrentResponse: (text: string) => void;
    setSelectedVoice: (voice: 'male' | 'female') => void;
    addUserFact: (fact: string) => void;
    clearMessages: () => void;
    clearError: () => void;
}

export const useVoicePipelineStore = create<VoicePipelineStore>((set) => ({
    state: 'idle',
    isOnline: true,
    error: null,
    messages: [],
    currentTranscript: '',
    currentResponse: '',
    selectedVoice: 'male',
    userFacts: [],

    setState: (state) => set({ state }),
    setIsOnline: (isOnline) => set({ isOnline }),
    setError: (error) => set({ error, state: error ? 'error' : 'idle' }),
    addMessage: (message) => set((s) => ({
        messages: [...s.messages.slice(-20), message]
    })),
    setCurrentTranscript: (currentTranscript) => set({ currentTranscript }),
    setCurrentResponse: (currentResponse) => set({ currentResponse }),
    setSelectedVoice: (selectedVoice) => set({ selectedVoice }),
    addUserFact: (fact) => set((s) => ({
        userFacts: [...new Set([...s.userFacts, fact])]
    })),
    clearMessages: () => set({ messages: [], currentTranscript: '', currentResponse: '' }),
    clearError: () => set({ error: null, state: 'idle' }),
}));

const PYTHON_BACKEND = 'http://127.0.0.1:5000';

export function useVoicePipeline() {
    const store = useVoicePipelineStore();
    const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);
    const isProcessingRef = useRef(false);

    // Check Python backend health with retries and detailed logging
    const checkBackendHealth = useCallback(async (): Promise<boolean> => {
        const maxRetries = 20;  // More retries
        const retryDelay = 500; // 500ms between retries

        console.log('🔌 Connecting to Python backend at http://127.0.0.1:5000...');

        for (let attempt = 1; attempt <= maxRetries; attempt++) {
            try {
                console.log(`🔍 Health check attempt ${attempt}/${maxRetries}...`);

                // Create abort controller with longer timeout
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 5000); // 5 second timeout

                const response = await fetch('http://127.0.0.1:5000/health', {
                    method: 'GET',
                    headers: {
                        'Accept': 'application/json',
                    },
                    signal: controller.signal,
                });

                clearTimeout(timeoutId);

                if (response.ok) {
                    const data = await response.json();
                    console.log('📡 Backend response:', data);

                    if (data.status === 'ok') {
                        console.log('✅ Backend connected successfully!');
                        return true;
                    }
                } else {
                    console.log(`⚠️ Backend returned status: ${response.status}`);
                }
            } catch (error: any) {
                if (error.name === 'AbortError') {
                    console.log(`⏱️ Attempt ${attempt} timed out`);
                } else {
                    console.log(`⏳ Attempt ${attempt} failed:`, error.message);
                }
            }

            if (attempt < maxRetries) {
                await new Promise(resolve => setTimeout(resolve, retryDelay));
            }
        }

        console.log('❌ Could not connect to backend after all retries');
        return false;
    }, []);

    // Check internet connectivity (separate from backend)
    const checkConnectivity = useCallback(async () => {
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 5000);

            await fetch('https://www.google.com/favicon.ico', {
                mode: 'no-cors',
                cache: 'no-store',
                signal: controller.signal
            });

            clearTimeout(timeoutId);
            store.setIsOnline(true);
            return true;
        } catch {
            store.setIsOnline(false);
            return false;
        }
    }, []);

    // Start wake word detection
    const startListening = useCallback(async () => {
        console.log('🎤 Initializing voice pipeline...');

        const backendOk = await checkBackendHealth();

        if (!backendOk) {
            store.setError('Python backend not running. Start with: python3.11 jarvis/python/main.py');
            console.error('❌ Backend not available');
            return;
        }

        // Clear any previous errors
        store.setError(null);

        try {
            console.log('🎯 Starting wake word detection...');

            const response = await fetch('http://127.0.0.1:5000/wake-word/start', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
            });

            const data = await response.json();
            console.log('📡 Wake word response:', data);

            if (data.status === 'started' || data.status === 'already_listening') {
                store.setState('idle');
                console.log('✅ Wake word detection active!');

                // Start polling for wake word
                pollingRef.current = setInterval(async () => {
                    if (isProcessingRef.current) return;

                    try {
                        const pollResponse = await fetch('http://127.0.0.1:5000/wake-word/poll');
                        const pollData = await pollResponse.json();

                        if (pollData.detected) {
                            console.log('✨ Wake word detected!');
                            await handleWakeWordDetected();
                        }
                    } catch (e) {
                        // Silently ignore polling errors
                    }
                }, 200);
            } else {
                store.setError('Failed to start wake word: ' + (data.message || 'Unknown error'));
            }
        } catch (error) {
            const errorMsg = error instanceof Error ? error.message : String(error);
            console.error('❌ Error starting wake word:', errorMsg);
            store.setError('Failed to connect: ' + errorMsg);
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [checkBackendHealth]);

    // Handle wake word detection
    const handleWakeWordDetected = useCallback(async () => {
        if (isProcessingRef.current) return;
        isProcessingRef.current = true;

        try {
            store.setState('listening');
            store.setCurrentTranscript('');
            store.setCurrentResponse('');

            // Record audio
            console.log('Recording...');
            const recordResponse = await fetch(PYTHON_BACKEND + '/audio/record', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    max_duration: 10,
                    silence_threshold: 500,
                    silence_duration: 1.5
                })
            });
            const recordData = await recordResponse.json();

            if (!recordData.success || !recordData.audio_base64) {
                store.setState('idle');
                isProcessingRef.current = false;
                return;
            }

            // Transcribe
            store.setState('processing');
            console.log('Transcribing...');
            const transcribeResponse = await fetch(PYTHON_BACKEND + '/stt/transcribe', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ audio_base64: recordData.audio_base64 })
            });
            const transcribeData = await transcribeResponse.json();

            if (!transcribeData.success || !transcribeData.text?.trim()) {
                await speakText("I didn't catch that. Could you try again?");
                store.setState('idle');
                isProcessingRef.current = false;
                return;
            }

            const userText = transcribeData.text.trim();
            store.setCurrentTranscript(userText);
            store.addMessage({ role: 'user', content: userText, timestamp: new Date() });

            // Get AI response
            store.setState('thinking');
            console.log('Getting AI response...');

            const aiResponse = await getAIResponse(userText, store.messages, store.userFacts);

            // Parse actions from response
            const { cleanResponse, actions } = parseActionsFromResponse(aiResponse);

            store.setCurrentResponse(cleanResponse);
            store.addMessage({ role: 'assistant', content: cleanResponse, timestamp: new Date() });

            // Handle any actions (like SAVE_FACT)
            for (const action of actions) {
                if (action.action === 'SAVE_FACT' && action.params?.fact) {
                    store.addUserFact(action.params.fact);
                }
            }

            // Speak response
            store.setState('speaking');
            console.log('Speaking...');
            await speakText(cleanResponse);

            store.setState('idle');

        } catch (error) {
            console.error('Pipeline error:', error);
            const errorMsg = error instanceof Error ? error.message : String(error);
            store.setError('Error: ' + errorMsg);
        } finally {
            isProcessingRef.current = false;
        }
    }, []);

    // Stop listening
    const stopListening = useCallback(async () => {
        if (pollingRef.current) {
            clearInterval(pollingRef.current);
            pollingRef.current = null;
        }

        try {
            await fetch(PYTHON_BACKEND + '/wake-word/stop', { method: 'POST' });
        } catch (e) {
            console.error('Error stopping:', e);
        }

        store.setState('idle');
    }, []);

    // Manual trigger
    const triggerManually = useCallback(async () => {
        if (!isProcessingRef.current) {
            await handleWakeWordDetected();
        }
    }, [handleWakeWordDetected]);

    // Initialize on mount
    useEffect(() => {
        checkConnectivity();
        startListening();

        const connectivityInterval = setInterval(checkConnectivity, 30000);

        return () => {
            clearInterval(connectivityInterval);
            stopListening();
        };
    }, []);

    return {
        state: store.state,
        isOnline: store.isOnline,
        error: store.error,
        messages: store.messages,
        currentTranscript: store.currentTranscript,
        currentResponse: store.currentResponse,
        selectedVoice: store.selectedVoice,

        startListening,
        stopListening,
        triggerManually,
        setVoice: store.setSelectedVoice,
        clearMessages: store.clearMessages,
        clearError: store.clearError,
    };
}

// ============== Helper Functions ==============

async function speakText(text: string): Promise<void> {
    try {
        await fetch(PYTHON_BACKEND + '/tts/speak', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text, voice: 'male', play: true })
        });
    } catch (error) {
        console.error('TTS error:', error);
    }
}

async function getAIResponse(
    userMessage: string,
    history: Message[],
    userFacts: string[]
): Promise<string> {
    // Build conversation for LLM
    const messages = history.slice(-10).map(m => ({
        role: m.role,
        content: m.content
    }));
    messages.push({ role: 'user', content: userMessage });

    // Build system prompt
    const systemPrompt = buildSystemPrompt(userFacts);

    // Try Gemini first, then OpenRouter, then Ollama
    const providers = [
        () => callGemini(messages, systemPrompt),
        () => callOpenRouter(messages, systemPrompt),
        () => callOllama(messages, systemPrompt),
    ];

    for (const provider of providers) {
        try {
            const response = await provider();
            if (response) return response;
        } catch (error) {
            console.log('Provider failed, trying next... ', error);
        }
    }

    return "I'm having trouble connecting to my brain. Please check your API keys or internet connection.";
}

function buildSystemPrompt(userFacts: string[]): string {
    const factsSection = userFacts.length > 0
        ? 'Things I know about you:\n' + userFacts.map(f => '- ' + f).join('\n')
        : 'I don\'t have any saved information about you yet.';

    return `You are Jarvis, a helpful AI assistant. Be concise (1-3 sentences for voice).

${factsSection}

When you learn something about the user, save it: 
\`\`\`action
{"action": "SAVE_FACT", "params": {"fact": "User's name is Alex"}}
\`\`\`

Available actions:  SAVE_FACT, SEND_EMAIL, GET_WEATHER, SEARCH_WEB, OPEN_APP, CREATE_CALENDAR_EVENT

Always respond conversationally. `;
}

async function callGemini(messages: any[], systemPrompt: string): Promise<string> {
    // Try multiple ways to get the API key
    const apiKey = process.env.GEMINI_API_KEY_1
        || process.env.VITE_GEMINI_API_KEY_1
        || (window as any).GEMINI_API_KEY_1;

    console.log('🔑 Gemini API key found:', apiKey ? 'Yes' : 'No');

    if (!apiKey) {
        console.log('⚠️ No Gemini API key, trying next provider...');
        throw new Error('No Gemini API key');
    }

    console.log('🚀 Calling Gemini API...');

    const response = await fetch(
        'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=' + apiKey,
        {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                systemInstruction: { parts: [{ text: systemPrompt }] },
                contents: messages.map(m => ({
                    role: m.role === 'user' ? 'user' : 'model',
                    parts: [{ text: m.content }]
                })),
                generationConfig: { temperature: 0.7, maxOutputTokens: 1024 }
            })
        }
    );

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        console.error('❌ Gemini API error:', errorData);
        throw new Error('Gemini API error: ' + (errorData.error?.message || response.statusText));
    }

    const data = await response.json();
    console.log('✅ Gemini response received');
    return data.candidates?.[0]?.content?.parts?.[0]?.text || '';
}

async function callOpenRouter(messages: any[], systemPrompt: string): Promise<string> {
    const apiKey = process.env.OPENROUTER_API_KEY
        || process.env.VITE_OPENROUTER_API_KEY
        || (window as any).OPENROUTER_API_KEY;

    console.log('🔑 OpenRouter API key found:', apiKey ? 'Yes' : 'No');

    if (!apiKey) {
        console.log('⚠️ No OpenRouter API key, trying next provider...');
        throw new Error('No OpenRouter API key');
    }

    console.log('🚀 Calling OpenRouter API...');

    const response = await fetch('https://openrouter.ai/api/v1/chat/completions', {
        method: 'POST',
        headers: {
            'Authorization': 'Bearer ' + apiKey,
            'Content-Type': 'application/json',
            'HTTP-Referer': 'https://jarvis-assistant.local',
        },
        body: JSON.stringify({
            model: 'meta-llama/llama-3.3-70b-instruct:free',
            messages: [
                { role: 'system', content: systemPrompt },
                ...messages
            ]
        })
    });

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        console.error('❌ OpenRouter error:', errorData);
        throw new Error('OpenRouter error');
    }

    const data = await response.json();
    console.log('✅ OpenRouter response received');
    return data.choices?.[0]?.message?.content || '';
}

async function callOllama(messages: any[], systemPrompt: string): Promise<string> {
    const response = await fetch('http://localhost:11434/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            model: 'tinyllama',
            messages: [
                { role: 'system', content: systemPrompt },
                ...messages
            ],
            stream: false
        })
    });

    if (!response.ok) throw new Error('Ollama error');
    const data = await response.json();
    return data.message?.content || '';
}

interface ParsedAction {
    action: string;
    params: Record<string, any>;
}

function parseActionsFromResponse(response: string): { cleanResponse: string; actions: ParsedAction[] } {
    const actionRegex = /```action\n([\s\S]*?)\n```/g;
    const actions: ParsedAction[] = [];

    let match;
    while ((match = actionRegex.exec(response)) !== null) {
        try {
            actions.push(JSON.parse(match[1]));
        } catch (e) {
            console.error('Failed to parse action:', match[1]);
        }
    }

    const cleanResponse = response.replace(/```action\n[\s\S]*?\n```/g, '').trim();

    return { cleanResponse, actions };
}
