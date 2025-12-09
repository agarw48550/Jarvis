import React from 'react';
import { motion } from 'framer-motion';

const stateColors: Record<string, string> = {
    idle: 'from-slate-500 to-slate-600',
    listening: 'from-blue-500 to-cyan-400',
    processing: 'from-yellow-500 to-orange-400',
    thinking: 'from-purple-500 to-pink-500',
    speaking: 'from-emerald-500 to-teal-400',
    error: 'from-red-500 to-red-600',
};

interface VoiceOrbProps {
    state: 'idle' | 'listening' | 'processing' | 'thinking' | 'speaking' | 'error';
}

export function VoiceOrb({ state }: VoiceOrbProps) {
    const colorClass = stateColors[state] || stateColors.idle;

    return (
        <div className="relative">
            {/* Glow effect */}
            <motion.div
                className={`absolute inset-0 rounded-full bg-gradient-to-r ${colorClass} blur-2xl opacity-50`}
                animate={{
                    scale: state === 'idle' ? 1 : [1, 1.2, 1],
                    opacity: state === 'idle' ? 0.3 : 0.6,
                }}
                transition={{ repeat: Infinity, duration: 2 }}
            />

            {/* Main orb */}
            <motion.div
                className={`relative w-48 h-48 rounded-full bg-gradient-to-br ${colorClass} 
                    shadow-2xl backdrop-blur-sm border border-white/20`}
                animate={{
                    scale: state === 'listening' ? [1, 1.05, 1] : 1,
                }}
                transition={{ repeat: Infinity, duration: 1.5 }}
            >
                {/* Inner pulse */}
                <motion.div
                    className="absolute inset-4 rounded-full bg-white/20"
                    animate={{
                        scale: state !== 'idle' ? [0.8, 1, 0.8] : 1,
                        opacity: state !== 'idle' ? [0.5, 1, 0.5] : 0.3,
                    }}
                    transition={{ repeat: Infinity, duration: 1 }}
                />
            </motion.div>

            {/* State label */}
            <motion.p
                className="absolute -bottom-12 left-1/2 -translate-x-1/2 text-white/60 text-sm capitalize whitespace-nowrap"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
            >
                {state === 'idle' ? 'Say "Hey Jarvis"' : state}
            </motion.p>
        </div>
    );
}
