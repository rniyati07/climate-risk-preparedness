import React from 'react';
import { Menu, Trash2, ShieldAlert } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const TopBar = ({ hazardType, onClearSession, onMenuClick }) => {
  return (
    <div className="sticky top-0 z-20 w-full bg-background/80 backdrop-blur-md border-b border-divider px-4 h-14 flex items-center justify-between">
      
      <div className="flex items-center gap-3">
        <button className="md:hidden text-muted hover:text-body" onClick={onMenuClick}>
          <Menu className="w-5 h-5" />
        </button>
        <span className="font-heading font-medium text-[15px] text-heading">
          New Conversation
        </span>
      </div>

      {/* Center Hazard Chip */}
      <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2">
        <AnimatePresence mode="wait">
          {hazardType && (
            <motion.div 
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="flex items-center gap-1.5 px-3 py-1 rounded-full border border-[var(--border-accent)] bg-[var(--glow)] hazard-transition"
            >
              <ShieldAlert className="w-3.5 h-3.5 text-[var(--accent)] hazard-transition" />
              <span className="font-mono text-[11px] text-[var(--accent)] hazard-transition tracking-wide uppercase">
                {hazardType} Detected
              </span>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <button 
        onClick={onClearSession}
        className="text-muted hover:text-body transition-colors flex items-center gap-2"
        title="Clear Session"
      >
        <span className="hidden sm:inline font-body text-xs">Clear</span>
        <Trash2 className="w-4 h-4" />
      </button>
      
    </div>
  );
};

export default TopBar;
