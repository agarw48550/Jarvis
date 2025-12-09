import React from 'react';
import { VoiceOrb } from './components/Assistant/VoiceOrb';
import { WaveformVisualizer } from './components/Assistant/WaveformVisualizer';
import './index.css';

import { useVoicePipeline } from './hooks/useVoicePipeline';

export default function App() {
    const { state, isOnline } = useVoicePipeline();

    return (
        <div className="h-screen bg-gradient-to-br from-dark-950 via-dark-900 to-primary-900 flex flex-col text-white">
            {/* Custom Title Bar */}
            <div className="h-[30px] w-full drag-region" style={{ WebkitAppRegion: 'drag' } as any} />

            {/* Status Bar */}
            <div className="px-4 py-2 text-xs text-white/40 flex justify-between items-center">
                <span>JARVIS V3</span>
                <div className="flex items-center gap-2">
                    <div className={`w-2 h-2 rounded-full ${isOnline ? 'bg-emerald-500' : 'bg-red-500'} shadow-[0_0_10px_rgba(16,185,129,0.5)]`}></div>
                    <span>{isOnline ? 'ONLINE' : 'OFFLINE'}</span>
                </div>
            </div>

            {/* Main Content */}
            <main className="flex-1 flex flex-col items-center justify-center p-8">
                {/* Voice Orb */}
                <VoiceOrb state={state} />

                {/* Waveform Placeholder - hidden for now until we have audio */}
                {state !== 'idle' && <WaveformVisualizer />}

                {/* Greeting */}
                <div className="mt-12 text-center opacity-80">
                    <h1 className="text-2xl font-light tracking-wider">How can I help you, Sir?</h1>
                </div>
            </main>
        </div>
    );
}
