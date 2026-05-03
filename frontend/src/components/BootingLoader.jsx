import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const BootingLoader = () => {
  const [phase, setPhase] = useState(1);

  useEffect(() => {
    const t1 = setTimeout(() => setPhase(2), 800); // slightly longer for visual effect
    const t2 = setTimeout(() => setPhase(3), 1800);
    return () => { clearTimeout(t1); clearTimeout(t2); };
  }, []);

  const getPhaseText = () => {
    switch(phase) {
      case 1: return "Classifying hazard context...";
      case 2: return "Retrieving government guidelines...";
      case 3: return "Generating structured response...";
      default: return "";
    }
  };

  return (
    <div className="flex flex-col items-center justify-center gap-4 py-4 min-h-[80px]">
      <div className="relative w-12 h-12 flex items-center justify-center">
        
        {/* Phase 1: Central Orb */}
        <motion.div
          className="absolute w-4 h-4 rounded-full bg-[var(--accent)] shadow-glow hazard-transition"
          animate={{ scale: [0.95, 1.05, 0.95] }}
          transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
        />

        {/* Phase 2: Orbital Arcs */}
        <AnimatePresence>
          {phase >= 2 && (
            <motion.svg 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="absolute inset-0 w-full h-full"
              viewBox="0 0 48 48"
            >
              {/* Outer Arc */}
              <motion.circle
                cx="24" cy="24" r="18"
                fill="none"
                stroke="var(--accent)"
                strokeWidth="1.5"
                strokeDasharray="30 80"
                strokeLinecap="round"
                className="hazard-transition"
                animate={{ rotate: 360 }}
                transition={{ duration: 4, repeat: Infinity, ease: "linear" }}
                style={{ transformOrigin: "center" }}
              />
              {/* Inner Arc */}
              <motion.circle
                cx="24" cy="24" r="12"
                fill="none"
                stroke="var(--accent)"
                strokeWidth="1"
                strokeDasharray="20 60"
                strokeLinecap="round"
                className="hazard-transition"
                animate={{ rotate: -360 }}
                transition={{ duration: 3, repeat: Infinity, ease: "linear" }}
                style={{ transformOrigin: "center" }}
              />
            </motion.svg>
          )}
        </AnimatePresence>

        {/* Phase 3: Data Fragments */}
        <AnimatePresence>
          {phase >= 3 && (
            <>
              {[0, 1, 2].map((i) => (
                <motion.div
                  key={i}
                  className="absolute w-1 h-1 bg-[var(--accent)] rounded-full hazard-transition"
                  initial={{ opacity: 0, x: 0, y: 0 }}
                  animate={{ 
                    opacity: [0, 1, 0],
                    x: Math.cos((i * 120 * Math.PI) / 180) * 24,
                    y: Math.sin((i * 120 * Math.PI) / 180) * 24
                  }}
                  transition={{ 
                    duration: 1.5, 
                    repeat: Infinity, 
                    delay: i * 0.5,
                    ease: "easeOut"
                  }}
                />
              ))}
            </>
          )}
        </AnimatePresence>

      </div>
      
      {/* Text updates with fade */}
      <AnimatePresence mode="wait">
        <motion.span
          key={phase}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.3 }}
          className="font-mono text-xs text-muted"
        >
          {getPhaseText()}
        </motion.span>
      </AnimatePresence>
    </div>
  );
};

export default BootingLoader;
