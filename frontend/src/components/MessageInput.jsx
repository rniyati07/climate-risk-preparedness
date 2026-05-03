import React, { useState, useRef, useEffect } from 'react';
import { ArrowUp } from 'lucide-react';

const QUICK_PROMPTS = [
  "What to do in a flood?",
  "Emergency kit checklist",
  "Cyclone evacuation steps",
  "Heatwave symptoms & care",
  "Government emergency contacts"
];

const MessageInput = ({ onSendMessage }) => {
  const [input, setInput] = useState('');
  const textareaRef = useRef(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = '52px';
      const scrollHeight = textareaRef.current.scrollHeight;
      textareaRef.current.style.height = Math.min(scrollHeight, 160) + 'px';
    }
  }, [input]);

  const handleSend = () => {
    if (input.trim()) {
      onSendMessage(input.trim());
      setInput('');
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="sticky bottom-0 z-20 w-full glass-input border-t border-divider p-4 md:px-24 flex flex-col gap-3">
      
      {/* Quick Prompts (horizontal scroll) */}
      <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-hide -mx-4 px-4 md:mx-0 md:px-0">
        {QUICK_PROMPTS.map((prompt, idx) => (
          <button
            key={idx}
            onClick={() => onSendMessage(prompt)}
            className="shrink-0 px-3 py-1.5 rounded-full border border-divider text-muted font-mono text-xs hover:text-body hover:border-[var(--border-accent)] hover:bg-[var(--glow)] transition-all hazard-transition"
          >
            {prompt}
          </button>
        ))}
      </div>

      {/* Input Area */}
      <div className="relative w-full max-w-3xl mx-auto">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask ARIA about flood safety, cyclone preparedness..."
          className="w-full bg-surface border border-divider rounded-xl pl-4 pr-14 py-3.5 text-[15px] font-body text-body placeholder:text-muted focus:outline-none focus:border-[var(--accent)] transition-colors hazard-transition resize-none min-h-[52px] max-h-[160px]"
          rows={1}
        />
        <button
          onClick={handleSend}
          disabled={!input.trim()}
          className="absolute right-2 top-1/2 -translate-y-1/2 w-9 h-9 rounded-full bg-[var(--accent)] hazard-transition flex items-center justify-center text-white disabled:opacity-30 disabled:hover:scale-100 hover:scale-[0.97] transition-all"
        >
          <ArrowUp className="w-4 h-4" strokeWidth={2.5} />
        </button>
      </div>

      <div className="text-center">
        <span className="font-mono text-[10px] text-muted opacity-60">
          ARIA may be approximate. For active emergencies call <strong className="text-body">112</strong> · NDRF <strong className="text-body">1078</strong>.
        </span>
      </div>
    </div>
  );
};

export default MessageInput;
