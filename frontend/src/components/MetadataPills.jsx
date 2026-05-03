import React from 'react';
import { FileText } from 'lucide-react';

export const MetadataPills = ({ citations, metadata }) => {
  return (
    <div className="flex flex-col gap-3 mt-4 pt-4 border-t border-divider">
      
      {/* Citations Row */}
      {citations && citations.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {citations.map((cite, idx) => (
            <button 
              key={idx}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-white/5 border border-white/10 hover:bg-white/10 hover:border-white/20 transition-all cursor-pointer group"
            >
              <FileText className="w-3 h-3 text-muted group-hover:text-body transition-colors" />
              <span className="font-mono text-[11px] text-muted group-hover:text-body transition-colors">
                [{cite}]
              </span>
            </button>
          ))}
        </div>
      )}

      {/* Metadata Chips Row */}
      <div className="flex flex-wrap gap-2">
        {metadata.hazard && (
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-white/5 border border-white/10">
            <div className="w-1.5 h-1.5 rounded-full bg-[var(--accent)] hazard-transition" />
            <span className="font-mono text-[11px] text-muted">Hazard: <strong className="text-body font-normal">{metadata.hazard}</strong></span>
          </div>
        )}
        
        {metadata.intent && (
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-white/5 border border-white/10">
            <div className="w-1.5 h-1.5 rounded-full bg-[var(--accent)] hazard-transition" />
            <span className="font-mono text-[11px] text-muted">Intent: <strong className="text-body font-normal">{metadata.intent}</strong></span>
          </div>
        )}

        {metadata.confidence && (
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-white/5 border border-white/10">
            <div className={`w-1.5 h-1.5 rounded-full ${
              metadata.confidence > 85 ? 'bg-green-500' : 
              metadata.confidence > 60 ? 'bg-amber-500' : 'bg-red-500'
            }`} />
            <span className="font-mono text-[11px] text-muted">{metadata.confidence}% Confidence</span>
          </div>
        )}

        {metadata.time && (
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-white/5 border border-white/10">
            <span className="font-mono text-[11px] text-muted">{metadata.time}</span>
          </div>
        )}

        {metadata.sources && (
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-white/5 border border-white/10">
            <div className="w-1.5 h-1.5 rounded-full bg-green-500" />
            <span className="font-mono text-[11px] text-muted">✓ {metadata.sources} documents</span>
          </div>
        )}
      </div>

    </div>
  );
};
