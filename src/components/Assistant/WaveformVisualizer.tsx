import React from 'react';
import { motion } from 'framer-motion';

export function WaveformVisualizer() {
    return (
        <div className="flex justify-center items-center gap-1 h-8 mt-8">
            {[...Array(5)].map((_, i) => (
                <motion.div
                    key={i}
                    className="w-1 bg-white/80 rounded-full"
                    animate={{
                        height: [10, 24, 10],
                    }}
                    transition={{
                        repeat: Infinity,
                        duration: 0.8,
                        delay: i * 0.1,
                    }}
                />
            ))}
        </div>
    );
}
