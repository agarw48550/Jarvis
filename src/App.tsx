// jarvis/src/App.tsx
/**
 * Jarvis AI Assistant - Main Application (FIXED)
 */

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useVoicePipeline, PipelineState } from './hooks/useVoicePipeline';

// State configurations
const stateConfig: Record<PipelineState, { gradient: string; glow: string; label: string }> = {
    idle: {
        gradient: 'from-slate-600 via-slate-500 to-slate-600',
        glow: 'rgba(100, 116, 139, 0.4)',
        label: 'Say "Hey Jarvis"',
    },
    listening: {
        gradient: 'from-blue-500 via-cyan-400 to-blue-500',
        glow: 'rgba(59, 130, 246, 0.6)',
        label: 'Listening...',
    },
    processing: {
        gradient: 'from-yellow-500 via-orange-400 to-yellow-500',
        glow: 'rgba(234, 179, 8, 0.5)',
        label: 'Processing...',
    },
    thinking: {
        gradient: 'from-purple-500 via-pink-500 to-purple-500',
        glow: 'rgba(168, 85, 247, 0.6)',
        label: 'Thinking...',
    },
    speaking: {
        gradient: 'from-emerald-500 via-teal-400 to-emerald-500',
        glow: 'rgba(16, 185, 129, 0.6)',
        label: 'Speaking...',
    },
    error: {
        gradient: 'from-red-500 via-red-600 to-red-500',
        glow: 'rgba(239, 68, 68, 0.5)',
        label: 'Error',
    },
};

// Voice Orb Component
function VoiceOrb({ state, onClick }: { state: PipelineState; onClick?: () => void }) {
    const config = stateConfig[state];
    const isActive = state !== 'idle' && state !== 'error';

    return (
        <button
            onClick={onClick}
            className="relative flex flex-col items-center cursor-pointer group focus:outline-none"
        >
            {/* Outer glow */}
            <motion.div
                className="absolute w-48 h-48 rounded-full blur-3xl opacity-50"
                style={{ backgroundColor: config.glow }}
                animate={{
                    scale: isActive ? [1, 1.3, 1] : 1,
                    opacity: isActive ? [0.4, 0.7, 0.4] : 0.3,
                }}
                transition={{ repeat: Infinity, duration: 2, ease: 'easeInOut' }}
            />

            {/* Main orb */}
            <motion.div
                className={`relative w-36 h-36 rounded-full bg-gradient-to-br ${config.gradient} 
                    shadow-2xl border border-white/20 backdrop-blur-sm overflow-hidden
                    group-hover:scale-105 transition-transform`}
                animate={{ scale: isActive ? [1, 1.05, 1] : 1 }}
                transition={{ repeat: Infinity, duration: 1.5, ease: 'easeInOut' }}
            >
                {/* Inner shine */}
                <div className="absolute inset-0 bg-gradient-to-t from-transparent via-white/10 to-white/30 rounded-full" />

                {/* Pulse rings when active */}
                <AnimatePresence>
                    {isActive && (
                        <>
                            <motion.div
                                className="absolute inset-0 rounded-full border-2 border-white/30"
                                initial={{ scale: 0.8, opacity: 0 }}
                                animate={{ scale: [1, 1.6], opacity: [0.5, 0] }}
                                transition={{ repeat: Infinity, duration: 1.5 }}
                            />
                            <motion.div
                                className="absolute inset-0 rounded-full border-2 border-white/20"
                                initial={{ scale: 0.8, opacity: 0 }}
                                animate={{ scale: [1, 2], opacity: [0.3, 0] }}
                                transition={{ repeat: Infinity, duration: 1.5, delay: 0.3 }}
                            />
                        </>
                    )}
                </AnimatePresence>
            </motion.div>

            {/* State label */}
            <motion.p
                className="mt-6 text-white/70 text-sm font-medium tracking-wide"
                key={state}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
            >
                {config.label}
            </motion.p>

            {state === 'idle' && (
                <p className="mt-2 text-white/40 text-xs">or click to activate</p>
            )}
        </button>
    );
}

// Status indicator
function StatusBar({ isOnline }: { isOnline: boolean }) {
    return (
        <div className="absolute top-4 right-4 flex items-center gap-2 px-3 py-1.5 bg-white/5 rounded-full backdrop-blur-md border border-white/10">
            <div className={`w-2 h-2 rounded-full ${isOnline ? 'bg-emerald-400' : 'bg-amber-400'}`} />
            <span className="text-xs text-white/60 font-medium">
                {isOnline ? 'Online' : 'Offline'}
            </span>
        </div>
    );
}

// Chat bubble
function ChatBubble({ type, text }: { type: 'user' | 'assistant'; text: string }) {
    const isUser = type === 'user';

    return (
        <motion.div
            className={`max-w-lg p-4 rounded-2xl backdrop-blur-md ${isUser
                ? 'bg-blue-500/20 border border-blue-400/30 ml-auto'
                : 'bg-white/10 border border-white/20'
                }`}
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
        >
            <p className="text-white/90 text-sm leading-relaxed">{text}</p>
        </motion.div>
    );
}

// Error banner
function ErrorBanner({ message, onDismiss }: { message: string; onDismiss: () => void }) {
    return (
        <motion.div
            className="absolute top-16 left-1/2 -translate-x-1/2 max-w-md px-4 py-3 
                 bg-red-500/20 border border-red-400/30 rounded-xl backdrop-blur-md
                 flex items-center gap-3"
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
        >
            <p className="text-red-300 text-sm flex-1">{message}</p>
            <button
                onClick={onDismiss}
                className="text-red-300 hover:text-red-100 text-lg font-bold"
            >
                ×
            </button>
        </motion.div>
    );
}

// Settings Modal
function SettingsModal({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
    if (!isOpen) return null;

    return (
        <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
            onClick={onClose}
        >
            <motion.div
                initial={{ scale: 0.95, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.95, opacity: 0 }}
                className="w-full max-w-md bg-slate-900/90 border border-white/10 rounded-2xl shadow-2xl overflow-hidden"
                onClick={e => e.stopPropagation()}
            >
                <div className="p-6 border-b border-white/10 flex justify-between items-center">
                    <h2 className="text-xl font-semibold text-white">Settings</h2>
                    <button onClick={onClose} className="text-white/50 hover:text-white transition-colors">×</button>
                </div>

                <div className="p-6 space-y-6">
                    {/* Voice Selection */}
                    <div className="space-y-3">
                        <label className="text-sm font-medium text-blue-200 uppercase tracking-wider">Voice</label>
                        <div className="grid grid-cols-2 gap-3">
                            {['Male', 'Female'].map((v) => (
                                <button key={v} className="px-4 py-2 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 transition-all text-sm">
                                    {v}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Wake Word */}
                    <div className="space-y-3">
                        <label className="text-sm font-medium text-blue-200 uppercase tracking-wider">Wake Word</label>
                        <div className="flex items-center justify-between px-4 py-3 rounded-lg bg-white/5 border border-white/10">
                            <span className="text-white/80">"Hey Jarvis"</span>
                            <div className="w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]"></div>
                        </div>
                    </div>
                </div>

                <div className="p-4 bg-black/20 text-center text-xs text-white/30">
                    v10.0.0 • Axon Core Online
                </div>
            </motion.div>
        </motion.div>
    );
}

// Main App
export default function App() {
    const {
        state,
        isOnline,
        error,
        currentTranscript,
        currentResponse,
        triggerManually,
        clearError,
    } = useVoicePipeline();

    const [isSettingsOpen, setIsSettingsOpen] = React.useState(false);

    return (
        <div className="h-screen w-screen bg-slate-950 flex flex-col items-center justify-center relative overflow-hidden font-sans select-none text-slate-100">

            {/* Dynamic Aurora Background */}
            <div className="absolute inset-0 animate-aurora opacity-60 pointer-events-none" />

            {/* Noise/Grain Overlay */}
            <div className="absolute inset-0 opacity-[0.03] pointer-events-none mix-blend-overlay"
                style={{ backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E")` }}
            />

            {/* Top Bar (Draggable Region) */}
            <div className="absolute top-0 left-0 right-0 h-10 flex items-center justify-end px-4 z-50 app-drag-region">
                <StatusBar isOnline={isOnline} />
            </div>

            {/* Error Banner */}
            <AnimatePresence>
                {error && <ErrorBanner message={error} onDismiss={clearError} />}
            </AnimatePresence>

            {/* Settings Modal */}
            <AnimatePresence>
                {isSettingsOpen && <SettingsModal isOpen={isSettingsOpen} onClose={() => setIsSettingsOpen(false)} />}
            </AnimatePresence>

            {/* Main Content */}
            <main className="relative z-10 flex flex-col items-center justify-center w-full max-w-4xl p-8 gap-12">

                {/* Header */}
                <motion.div
                    initial={{ opacity: 0, y: -20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="text-center space-y-2"
                >
                    <h1 className="text-5xl font-bold tracking-tighter bg-clip-text text-transparent bg-gradient-to-r from-white via-blue-100 to-white drop-shadow-lg">
                        JARVIS
                    </h1>
                    <p className="text-blue-200/60 text-sm tracking-widest uppercase font-medium">
                        Advanced Virtual Assistant
                    </p>
                </motion.div>

                {/* Central Interaction Zone */}
                <div className="relative group">
                    {/* The Orb */}
                    <VoiceOrb state={state} onClick={triggerManually} />
                </div>

                {/* Conversation Area - Glass Card */}
                <div className="w-full max-w-2xl min-h-[140px] flex flex-col justify-end">
                    <AnimatePresence mode="wait">
                        {/* Only show one active item to keep it clean, or stacking? Let's stack last 2 */}
                        {currentTranscript && (
                            <motion.div key="user-input" layout className="mb-4">
                                <ChatBubble type="user" text={currentTranscript} />
                            </motion.div>
                        )}
                        {currentResponse && (
                            <motion.div key="ai-response" layout>
                                <ChatBubble type="assistant" text={currentResponse} />
                            </motion.div>
                        )}
                        {!currentTranscript && !currentResponse && state === 'idle' && (
                            <motion.p
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                exit={{ opacity: 0 }}
                                className="text-center text-white/20 italic"
                            >
                                Ready for your command...
                            </motion.p>
                        )}
                    </AnimatePresence>
                </div>

            </main>

            {/* Footer / Controls */}
            <footer className="absolute bottom-6 flex gap-4">
                <button
                    onClick={() => setIsSettingsOpen(true)}
                    className="p-3 rounded-full hover:bg-white/10 text-white/50 hover:text-white transition-colors"
                >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /></svg>
                </button>
            </footer>
        </div>
    );
}
