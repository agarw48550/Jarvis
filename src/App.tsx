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

    return (
        <div className="h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-indigo-950 
                    flex flex-col items-center justify-center relative overflow-hidden">
            {/* Background effects */}
            <div className="absolute inset-0 overflow-hidden pointer-events-none">
                <div className="absolute top-1/4 -left-20 w-80 h-80 bg-blue-500/10 rounded-full blur-3xl" />
                <div className="absolute bottom-1/4 -right-20 w-80 h-80 bg-purple-500/10 rounded-full blur-3xl" />
            </div>

            {/* Status */}
            <StatusBar isOnline={isOnline} />

            {/* Error */}
            <AnimatePresence>
                {error && <ErrorBanner message={error} onDismiss={clearError} />}
            </AnimatePresence>

            {/* Main content */}
            <main className="relative z-10 flex flex-col items-center gap-8 p-8 w-full max-w-2xl">
                {/* Title */}
                <motion.h1
                    className="text-4xl font-bold text-white/90 tracking-tight"
                    initial={{ opacity: 0, y: -20 }}
                    animate={{ opacity: 1, y: 0 }}
                >
                    JARVIS
                </motion.h1>

                {/* Orb */}
                <VoiceOrb state={state} onClick={triggerManually} />

                {/* Conversation */}
                <div className="w-full space-y-4 mt-8 min-h-[120px]">
                    <AnimatePresence mode="popLayout">
                        {currentTranscript && (
                            <ChatBubble key="user" type="user" text={currentTranscript} />
                        )}
                        {currentResponse && (
                            <ChatBubble key="assistant" type="assistant" text={currentResponse} />
                        )}
                    </AnimatePresence>
                </div>
            </main>

            {/* Footer */}
            <footer className="absolute bottom-4 text-white/30 text-xs">
                Jarvis AI Assistant • Free & Open Source
            </footer>
        </div>
    );
}
