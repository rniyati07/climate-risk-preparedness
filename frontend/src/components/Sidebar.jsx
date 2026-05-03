import React from 'react';
import { Radar, Plus, MessageSquare, X, Trash2 } from 'lucide-react';

const HAZARD_COLORS = {
  general: '#6366F1',
  flood: '#00B4D8',
  cyclone: '#3B82F6',
  heatwave: '#EF4444',
  earthquake: '#8B5CF6',
  drought: '#F59E0B'
};

const formatRelativeTime = (timestamp) => {
  const diff = Date.now() - timestamp;
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);

  if (minutes < 1) return 'Just now';
  if (minutes < 60) return `${minutes}m ago`;
  if (hours < 24) return `${hours}h ago`;
  if (days === 1) return 'Yesterday';
  return new Date(timestamp).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
};

const Sidebar = ({ onClose, onClearSession, sessions = [], sessionId, onLoadSession, onDeleteSession }) => {
  return (
    <div className="flex flex-col h-full w-full">
      {/* Top Section */}
      <div className="p-4 flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Radar className="w-5 h-5 text-[var(--accent)] hazard-transition" strokeWidth={2} />
            <span className="font-syne font-bold tracking-wide text-heading">ARIA</span>
          </div>
          <button className="md:hidden text-muted hover:text-body" onClick={onClose}>
            <X className="w-5 h-5" />
          </button>
        </div>
        
        <button 
          onClick={onClearSession}
          className="w-full flex items-center justify-center gap-2 bg-[var(--accent)] text-white py-2.5 rounded-full font-heading font-medium text-[15px] hover:shadow-glow transition-all hazard-transition"
        >
          <Plus className="w-4 h-4" />
          New Chat
        </button>
      </div>

      {/* Session History Section */}
      <div className="flex-1 overflow-y-auto px-2 py-4">
        <div className="px-2 mb-3">
          <span className="font-mono text-[10px] text-muted opacity-60 uppercase tracking-widest">
            RECENT SESSIONS
          </span>
        </div>
        
        <div className="flex flex-col gap-1">
          {sessions.length === 0 ? (
            <div className="px-3 py-4 text-center">
              <span className="font-body text-[13px] text-muted opacity-70">No saved sessions</span>
            </div>
          ) : (
            sessions.map((session) => {
              const isActive = session.id === sessionId;
              const hazardColor = HAZARD_COLORS[session.hazard] || HAZARD_COLORS.general;

              return (
                <div key={session.id} className="relative group">
                  <button 
                    onClick={() => onLoadSession(session.id)}
                    className={`w-full flex flex-col text-left px-3 py-2.5 rounded-lg transition-colors border-l-[3px] 
                      ${isActive ? 'bg-surface border-[var(--accent)]' : 'hover:bg-elevated border-transparent'}
                    `}
                  >
                    <div className="flex items-center gap-2 mb-1 w-full">
                      <div 
                        className="w-1.5 h-1.5 rounded-full shrink-0" 
                        style={{ backgroundColor: isActive ? 'var(--accent)' : hazardColor }} 
                      />
                      <span className="font-mono text-[10px] text-muted tracking-wide uppercase truncate max-w-[80px]">
                        {isActive ? 'ACTIVE' : session.hazard}
                      </span>
                      <span className="font-mono text-[10px] text-muted ml-auto shrink-0 group-hover:opacity-0 transition-opacity">
                        {isActive ? 'Now' : formatRelativeTime(session.updatedAt)}
                      </span>
                    </div>
                    <span className="font-body text-[14px] text-body truncate w-full pr-4">
                      {session.title}
                    </span>
                  </button>
                  
                  {/* Delete Button (visible on hover) */}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onDeleteSession(session.id);
                    }}
                    className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 text-muted hover:text-[#EF4444] opacity-0 group-hover:opacity-100 transition-opacity bg-surface/80 rounded-md"
                    title="Delete session"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Bottom Section */}
      <div className="p-4 border-t border-divider flex flex-col gap-3">
        <div className="flex gap-3 text-xs font-body text-muted">
          <a href="#" className="hover:text-body transition-colors">About</a>
          <a href="#" className="hover:text-body transition-colors">Sources</a>
          <a href="#" className="hover:text-body transition-colors">Feedback</a>
        </div>
        <div className="flex flex-col gap-1">
          <span className="font-mono text-[10px] text-muted opacity-60">
            ARIA v1.0 · Beta
          </span>
          <span className="font-mono text-[10px] text-muted opacity-50">
            History saved locally on this device
          </span>
        </div>
      </div>
    </div>
  );
};

export default Sidebar;
