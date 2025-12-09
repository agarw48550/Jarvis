import { create } from 'zustand';
import { useEffect } from 'react';

type VoiceState = 'idle' | 'listening' | 'thinking' | 'speaking';

interface VoiceStore {
    state: VoiceState;
    transcript: string;
    response: string;
    isOnline: boolean;
    setState: (state: VoiceState) => void;
    setTranscript: (text: string) => void;
    setResponse: (text: string) => void;
    setIsOnline: (online: boolean) => void;
}

export const useVoiceStore = create<VoiceStore>((set) => ({
    state: 'idle',
    transcript: '',
    response: '',
    isOnline: true, // Default to true for now
    setState: (state) => set({ state }),
    setTranscript: (transcript) => set({ transcript }),
    setResponse: (response) => set({ response }),
    setIsOnline: (isOnline) => set({ isOnline }),
}));

export function useVoicePipeline() {
    const store = useVoiceStore();

    useEffect(() => {
        // Initial setup (e.g. check connectivity, start wake word)
        console.log('Voice pipeline initialized');

        // Placeholder: Start wake word detection
        // voiceService.startWakeWordDetection();

        return () => {
            // Cleanup
            // voiceService.stopWakeWordDetection();
        };
    }, []);

    return store;
}
