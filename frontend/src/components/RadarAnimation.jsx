import React from 'react';
import { motion } from 'framer-motion';

const RadarAnimation = () => {
  return (
    <div className="relative w-full max-w-lg aspect-square flex items-center justify-center">
      {/* Central Pulsing Orb */}
      <motion.div
        className="absolute w-12 h-12 rounded-full bg-[var(--accent)] shadow-glow z-10"
        animate={{ scale: [0.95, 1.05, 0.95] }}
        transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
      />

      {/* Orbital Rings container rotating */}
      <motion.div
        className="absolute inset-0 flex items-center justify-center"
        animate={{ rotate: 360 }}
        transition={{ duration: 30, repeat: Infinity, ease: "linear" }}
      >
        <svg viewBox="0 0 400 400" className="w-full h-full opacity-30">
          <circle cx="200" cy="200" r="80" fill="none" stroke="var(--accent)" strokeWidth="1" strokeDasharray="4 4" />
          <circle cx="200" cy="200" r="140" fill="none" stroke="var(--accent)" strokeWidth="1" />
          <circle cx="200" cy="200" r="190" fill="none" stroke="var(--accent)" strokeWidth="0.5" />
          
          {/* Scanning sweep */}
          <path d="M200 200 L200 10 A190 190 0 0 1 290 32 Z" fill="url(#radarGradient)" opacity="0.4" />
          
          <defs>
            <linearGradient id="radarGradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="var(--accent)" stopOpacity="1" />
              <stop offset="100%" stopColor="var(--accent)" stopOpacity="0" />
            </linearGradient>
          </defs>
        </svg>

        {/* Data chips on the rings. Since the container rotates, we counter-rotate the chips so they remain upright */}
        <DataChip angle={45} distance={140} label="Flood Risk" sub="High · Chennai" color="#00B4D8" />
        <DataChip angle={180} distance={190} label="Cyclone Biparjoy" sub="ETA 48hr · Gujarat" color="#F59E0B" />
        <DataChip angle={290} distance={100} label="Heatwave Advisory" sub="Active · Delhi NCR" color="#EF4444" />
      </motion.div>
    </div>
  );
};

const DataChip = ({ angle, distance, label, sub, color }) => {
  // Convert angle and distance to x, y positions relative to center
  const rad = (angle * Math.PI) / 180;
  const x = Math.cos(rad) * distance;
  const y = Math.sin(rad) * distance;

  return (
    <motion.div
      className="absolute glass-panel rounded-md px-3 py-1.5 flex flex-col gap-0.5"
      style={{
        left: `calc(50% + ${x}px)`,
        top: `calc(50% + ${y}px)`,
        transformOrigin: "center center",
      }}
      // Counter rotate to keep the text upright
      animate={{ rotate: -360 }}
      transition={{ duration: 30, repeat: Infinity, ease: "linear" }}
    >
      <div className="flex items-center gap-1.5">
        <div className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: color }} />
        <span className="text-[10px] font-mono text-muted uppercase tracking-wider">{label}</span>
      </div>
      <span className="text-xs font-body text-body">{sub}</span>
    </motion.div>
  );
};

export default RadarAnimation;
