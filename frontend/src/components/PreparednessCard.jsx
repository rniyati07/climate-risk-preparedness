import React from 'react';
import { motion } from 'framer-motion';

const PHASE_CONFIG = {
  BEFORE: {
    color: '#EF4444',
    badge: 'PRE-DISASTER'
  },
  DURING: {
    color: '#F59E0B',
    badge: 'ACTIVE EMERGENCY',
    isPulse: true,
    isBold: true
  },
  AFTER: {
    color: '#22C55E',
    badge: 'RECOVERY PHASE'
  },
  HEALTH: {
    color: '#8B5CF6',
    badge: 'MEDICAL GUIDANCE'
  }
};

export const PreparednessCard = ({ phase, items }) => {
  const config = PHASE_CONFIG[phase] || PHASE_CONFIG.BEFORE;

  return (
    <div 
      className="bg-surface rounded-xl p-5 mb-3 shadow-sm border border-divider"
      style={{ borderLeft: `3px solid ${config.color}` }}
      role="region"
      aria-label={`${config.badge} Phase`}
    >
      {/* Badge */}
      <div className="flex items-center mb-4">
        <div 
          className="flex items-center px-2 py-1 rounded-full border"
          style={{ 
            borderColor: `${config.color}40`, 
            backgroundColor: `${config.color}15`
          }}
        >
          {config.isPulse && (
            <motion.div 
              className="w-1.5 h-1.5 rounded-full mr-1.5"
              style={{ backgroundColor: config.color }}
              animate={{ opacity: [1, 0.4, 1] }}
              transition={{ duration: 1.5, repeat: Infinity }}
            />
          )}
          <span 
            className="font-mono text-[10px] font-bold tracking-wider uppercase"
            style={{ color: config.color }}
          >
            {config.badge}
          </span>
        </div>
      </div>

      {/* Content */}
      <div className="flex flex-col gap-3">
        {items.map((item, idx) => (
          <div 
            key={idx}
            className="flex items-start gap-3"
          >
            <div className="mt-1.5 shrink-0 w-1.5 h-1.5 bg-muted rounded-full" />
            <span className="font-body text-[13px] leading-relaxed transition-colors text-body">
              {item}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};
