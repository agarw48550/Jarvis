// jarvis/src/hooks/useVoicePipeline.ts
import { useState, useEffect, useCallback, useRef } from 'react';
import { create } from 'zustand';
import { pythonBridge } from '../services/python-bridge';

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
    selectedVoice: string;

    setState: (state: PipelineState) => void;
    setIsOnline: (online: boolean) => void;
    setError: (error: string | null) => void;
    addMessage: (message: Message) => void;
    setCurrentTranscript: (text: string) => void;
    setCurrentResponse: (text: string | ((prev: string) => string)) => void;
    clearMessages: () => void;
}

export const useVoicePipelineStore = create<VoicePipelineStore>((set, get) => ({
    state: 'idle',
    isOnline: true,
    error: null,
    messages: [],
    currentTranscript: '',
    currentResponse: '',
    selectedVoice: 'male',

    setState: (state) => set({ state }),
    setIsOnline: (isOnline) => set({ isOnline }),
    setError: (error) => set({ error, state: error ? 'error' : 'idle' }),
    addMessage: (message) => set((s) => ({
        messages: [...s.messages.slice(-50), message]
    })),
    setCurrentTranscript: (currentTranscript) => set({ currentTranscript }),
    setCurrentResponse: (textOrFn) => set((s) => ({
        currentResponse: typeof textOrFn === 'function' ? textOrFn(s.currentResponse) : textOrFn
    })),
    clearMessages: () => set({ messages: [], currentTranscript: '', currentResponse: '' }),
}));

// Constants for Audio Processing
const SAMPLE_RATE = 24000; // Gemini Live prefers 24kHz or 16kHz
const CHUNK_SIZE = 4096;

export function useVoicePipeline() {
    const store = useVoicePipelineStore();
    const wsRef = useRef<WebSocket | null>(null);
    const audioContextRef = useRef<AudioContext | null>(null);
    const processorRef = useRef<ScriptProcessorNode | null>(null);
    const streamRef = useRef<MediaStream | null>(null);
    const playbackQueueRef = useRef<Float32Array[]>([]);
    const isPlayingRef = useRef(false);
    const nextStartTimeRef = useRef(0);

    // Convert Float32 (Web Audio) to Int16 (Gemini)
    const floatTo16BitPCM = (input: Float32Array) => {
        const output = new Int16Array(input.length);
        for (let i = 0; i < input.length; i++) {
            const s = Math.max(-1, Math.min(1, input[i]));
            output[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
        }
        return output;
    };

    // Convert Base64 Int16 (Gemini) to Float32 (Web Audio)
    const base64ToFloat32 = (base64: string) => {
        const binary = atob(base64);
        const bytes = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
        const int16 = new Int16Array(bytes.buffer);
        const float32 = new Float32Array(int16.length);
        for (let i = 0; i < int16.length; i++) {
            float32[i] = int16[i] / 32768.0;
        }
        return float32;
    };

    const playNextChunk = useCallback(() => {
        if (!audioContextRef.current || playbackQueueRef.current.length === 0) {
            isPlayingRef.current = false;
            store.setState('idle'); // Back to listening/idle when done speaking
            return;
        }
        store.setState('speaking');

        const chunk = playbackQueueRef.current.shift();
        if (!chunk) return;

        const buffer = audioContextRef.current.createBuffer(1, chunk.length, SAMPLE_RATE);
        buffer.getChannelData(0).set(chunk);

        const source = audioContextRef.current.createBufferSource();
        source.buffer = buffer;
        source.connect(audioContextRef.current.destination);

        // Schedule seamlessly
        const currentTime = audioContextRef.current.currentTime;
        // If nextStartTime is in the past, reset it (gap happened)
        if (nextStartTimeRef.current < currentTime) {
            nextStartTimeRef.current = currentTime;
        }

        source.start(nextStartTimeRef.current);
        nextStartTimeRef.current += buffer.duration;

        isPlayingRef.current = true;

        // When this chunk ends, try scheduling next if queue not empty
        setTimeout(playNextChunk, (buffer.duration * 1000) / 1.5);
    }, []);

    const handleServerMessage = useCallback((data: any) => {
        if (!data || typeof data !== 'object' || !data.type) {
            console.warn('Invalid message format:', data);
            return;
        }

        if (data.type === 'audio') {
            if (typeof data.data !== 'string') {
                console.warn('Invalid audio data format');
                return;
            }
            // Audio Chunk from Gemini
            const float32 = base64ToFloat32(data.data);
            playbackQueueRef.current.push(float32);
            if (!isPlayingRef.current) {
                playNextChunk();
            }
        }
        else if (data.type === 'text') {
            if (typeof data.data !== 'string') {
                console.warn('Invalid text data format');
                return;
            }
            // Text update - use functional update to get fresh state
            store.setCurrentResponse((prev: string) => prev + data.data);
        }
    }, [playNextChunk]);

    const initConnection = useCallback(async () => {
        try {
            console.log('🔌 Connecting to WebSocket Live...');
            const ws = await pythonBridge.connectLive(handleServerMessage);
            wsRef.current = ws;

            ws.onclose = () => {
                console.log('WS Closed, retrying in 3s...');
                setTimeout(initConnection, 3000);
            };

            // Start Audio Capture
            await startAudioCapture();

        } catch (e) {
            console.error('Connection failed', e);
            store.setError('Failed to connect to Live API');
        }
    }, [handleServerMessage]);

    const startAudioCapture = async () => {
        try {
            if (!audioContextRef.current) {
                audioContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)({
                    sampleRate: SAMPLE_RATE
                });
            }

            const stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    channelCount: 1,
                    sampleRate: SAMPLE_RATE,
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true
                }
            });
            streamRef.current = stream;

            const source = audioContextRef.current.createMediaStreamSource(stream);
            processorRef.current = audioContextRef.current.createScriptProcessor(CHUNK_SIZE, 1, 1);

            processorRef.current.onaudioprocess = (e) => {
                if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;

                const inputData = e.inputBuffer.getChannelData(0);

                // Simple VAD / Volume check to skip silence
                let sum = 0;
                for (let i = 0; i < inputData.length; i++) sum += inputData[i] * inputData[i];
                const rms = Math.sqrt(sum / inputData.length);

                if (rms > 0.01) { // Threshold
                    store.setState('listening'); // We are hearing user

                    // Stop playback if user interrupts
                    if (isPlayingRef.current) {
                        playbackQueueRef.current = []; // Clear queue
                        nextStartTimeRef.current = 0;
                    }

                    // Convert and Send
                    const pcm16 = floatTo16BitPCM(inputData);

                    // Base64 encode raw bytes
                    let binary = '';
                    const bytes = new Uint8Array(pcm16.buffer);
                    const len = bytes.byteLength;
                    for (let i = 0; i < len; i++) {
                        binary += String.fromCharCode(bytes[i]);
                    }
                    const base64Data = btoa(binary);

                    wsRef.current.send(JSON.stringify({
                        type: "audio",
                        data: base64Data
                    }));
                }
            };

            source.connect(processorRef.current);
            // Connect through muted gain to avoid loopback while keeping processor active
            const gain = audioContextRef.current.createGain();
            gain.gain.value = 0;
            processorRef.current.connect(gain);
            gain.connect(audioContextRef.current.destination);

        } catch (e) {
            console.error('Mic Error', e);
            store.setError('Microphone access denied');
        }
    };

    useEffect(() => {
        initConnection();
        return () => {
            streamRef.current?.getTracks().forEach(t => t.stop());
            wsRef.current?.close();
            audioContextRef.current?.close();
        };
    }, []);

    // Placeholder actions
    return {
        state: store.state,
        isOnline: store.isOnline,
        error: store.error,
        messages: store.messages,
        currentTranscript: store.currentTranscript || (store.state === 'listening' ? 'Listening...' : ''),
        currentResponse: store.currentResponse,
        selectedVoice: store.selectedVoice,

        startListening: () => { },
        stopListening: () => { },
        triggerManually: () => { },
        setVoice: () => { },
        clearMessages: store.clearMessages,
        clearError: () => store.setError(null),
    };
}
