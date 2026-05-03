import React from 'react';
import { Radar, ArrowRight } from 'lucide-react';
import RadarAnimation from './RadarAnimation';
import QuickActionGrid from './QuickActionGrid';
import { motion } from 'framer-motion';

const HeroSection = ({ onStartChat }) => {
  return (
    <div className="relative w-full min-h-screen flex flex-col pt-8 px-6 md:px-12 lg:px-24 pb-16 overflow-hidden">
      {/* Top Left Wordmark */}
      <motion.div 
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.1 }}
        className="flex flex-col gap-1 z-20"
      >
        <div className="flex items-center gap-2">
          <Radar className="w-5 h-5 text-[var(--accent)] hazard-transition" strokeWidth={2} />
          <span className="font-syne font-bold text-xl tracking-wide text-heading">ARIA</span>
        </div>
        <span className="font-heading text-xs text-muted">Climate Risk Preparedness Advisor</span>
        <span className="font-mono text-[10px] text-muted opacity-60 mt-1 uppercase tracking-widest">
          Powered by NDMA · IMD · NDRF Guidelines
        </span>
      </motion.div>

      {/* Main Hero Content */}
      <div className="flex flex-col lg:flex-row items-center justify-between flex-1 mt-12 lg:mt-0 z-20">
        
        {/* Left Column - Text & CTA */}
        <div className="w-full lg:w-1/2 flex flex-col gap-8">
          <motion.h1 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="text-4xl md:text-5xl lg:text-6xl font-syne font-bold text-heading leading-[1.1] tracking-tight"
          >
            Know What To Do.<br />
            <span className="text-[var(--accent)] hazard-transition">Before It's Too Late.</span>
          </motion.h1>
          
          <motion.p 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.3 }}
            className="text-[17px] md:text-[18px] font-heading text-body leading-relaxed max-w-xl"
          >
            ARIA is an AI-powered climate risk advisor trained on verified government guidelines from NDMA, IMD, and NDRF. Ask anything — get structured, life-saving preparedness guidance instantly.
          </motion.p>

          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.4 }}
            className="flex flex-col sm:flex-row items-start sm:items-center gap-4 mt-2"
          >
            <button 
              onClick={() => onStartChat()}
              className="h-[52px] w-[180px] rounded-full bg-[var(--accent)] text-white font-syne font-medium flex items-center justify-center gap-2 hover:scale-[1.02] hover:shadow-glow transition-all hazard-transition"
            >
              Start Chat <ArrowRight className="w-4 h-4" />
            </button>
            <button 
              onClick={() => onStartChat("View Sample Response")}
              className="h-[52px] px-6 rounded-full border border-divider text-heading font-syne font-medium hover:bg-white/5 transition-colors"
            >
              View Sample Response
            </button>
          </motion.div>
          
          <motion.span 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.6, delay: 0.5 }}
            className="font-mono text-xs text-muted mt-2"
          >
            Free · No sign-in required · Government-verified sources
          </motion.span>
        </div>

        {/* Right Column - Visual */}
        <motion.div 
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.8, delay: 0.4 }}
          className="w-full lg:w-1/2 flex justify-center lg:justify-end mt-16 lg:mt-0"
        >
          <RadarAnimation />
        </motion.div>
      </div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.6 }}
      >
        <QuickActionGrid onActionClick={onStartChat} />
      </motion.div>

      {/* Ambient Gradient Background Overlay */}
      <div 
        className="absolute inset-0 pointer-events-none z-0 opacity-40 hazard-transition"
        style={{ background: 'var(--gradient-start)' }}
      >
        <div className="absolute inset-0 bg-gradient-to-br from-[var(--gradient-start)] to-[var(--gradient-end)] opacity-80 hazard-transition" />
      </div>
    </div>
  );
};

export default HeroSection;
