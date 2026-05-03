import React, { useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import { Radar } from 'lucide-react';
import BootingLoader from './BootingLoader';
import { PreparednessCard } from './PreparednessCard';
import { InformationMarkdown } from './InformationMarkdown';
import { MetadataPills } from './MetadataPills';

const MessageFeed = ({ messages, isGenerating }) => {
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isGenerating]);

  return (
    <div 
      ref={scrollRef}
      className="flex-1 overflow-y-auto px-4 py-8 md:px-12 scroll-smooth"
    >
      <div className="max-w-3xl mx-auto flex flex-col gap-6">
        
        {messages.length === 0 && !isGenerating && (
          <div className="flex flex-col items-center justify-center h-full text-center mt-20 gap-4 opacity-50">
            <Radar className="w-12 h-12 text-muted" strokeWidth={1} />
            <h2 className="font-heading text-xl text-heading">How can ARIA help you stay safe?</h2>
            <p className="font-body text-sm text-muted">Ask about any climate hazard. Responses are grounded in NDMA, IMD, and NDRF guidelines.</p>
          </div>
        )}

        {messages.map((msg, idx) => (
          <motion.div 
            key={idx}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
            className={`flex w-full ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            {msg.role === 'user' ? (
              // User Message
              <div className="flex flex-col items-end gap-1 max-w-[80%]">
                <span className="font-mono text-[11px] text-muted opacity-60 px-1">You</span>
                <div className="bg-[var(--glow)] border border-[var(--border-accent)] hazard-transition rounded-[16px_16px_4px_16px] px-4 py-3 text-[13px] font-body text-body">
                  {msg.content}
                </div>
              </div>
            ) : (
              // AI Message
              <div className="flex flex-col items-start w-full">
                <div className="flex items-center gap-1.5 mb-2 px-1">
                  <Radar className="w-3.5 h-3.5 text-muted" />
                  <span className="font-mono text-[11px] text-muted">ARIA</span>
                </div>
                
                <div className="w-full bg-surface border border-divider rounded-[4px_16px_16px_16px] p-5 md:p-6 border-l-[3px] border-l-[var(--accent)] hazard-transition shadow-sm">
                  
                  {/* Mode Renderers */}
                  {msg.mode === 'preparedness' ? (
                    <div className="flex flex-col">
                      {msg.phases?.map((phase, pIdx) => (
                        <PreparednessCard key={pIdx} phase={phase.type} items={phase.items} />
                      ))}
                    </div>
                  ) : (
                    <InformationMarkdown content={msg.content} />
                  )}

                  {/* Metadata and Citations */}
                  <MetadataPills citations={msg.citations} metadata={msg.metadata} />
                </div>
              </div>
            )}
          </motion.div>
        ))}

        {/* Loading State */}
        {isGenerating && (
          <motion.div 
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex justify-start w-full"
          >
            <div className="flex flex-col items-start w-full">
              <div className="flex items-center gap-1.5 mb-2 px-1">
                <Radar className="w-3.5 h-3.5 text-muted" />
                <span className="font-mono text-[11px] text-muted">ARIA</span>
              </div>
              <div className="w-full max-w-sm bg-surface border border-divider rounded-[4px_16px_16px_16px] p-5 border-l-[3px] border-l-[var(--accent)] hazard-transition">
                <BootingLoader />
              </div>
            </div>
          </motion.div>
        )}

      </div>
    </div>
  );
};

export default MessageFeed;
