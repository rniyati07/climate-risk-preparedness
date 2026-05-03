import React, { useState } from 'react';
import Sidebar from './Sidebar';
import TopBar from './TopBar';
import MessageInput from './MessageInput';
import MessageFeed from './MessageFeed';
import { Menu } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const ChatLayout = ({ hazardType, onClearSession, messages, isGenerating, onSendMessage, sessions, sessionId, onLoadSession, onDeleteSession }) => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <div className={`flex h-screen w-full overflow-hidden bg-background ${hazardType ? `hazard-${hazardType}` : ''}`}>
      
      {/* Desktop Sidebar */}
      <div className="hidden md:block w-60 shrink-0 border-r border-divider bg-[#0A0F1A] z-30">
        <Sidebar 
          onClose={() => {}} 
          onClearSession={onClearSession}
          sessions={sessions}
          sessionId={sessionId}
          onLoadSession={onLoadSession}
          onDeleteSession={onDeleteSession}
        />
      </div>

      {/* Mobile Sidebar Overlay */}
      <AnimatePresence>
        {mobileMenuOpen && (
          <>
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/60 z-40 md:hidden backdrop-blur-sm"
              onClick={() => setMobileMenuOpen(false)}
            />
            <motion.div
              initial={{ x: '-100%' }}
              animate={{ x: 0 }}
              exit={{ x: '-100%' }}
              transition={{ type: "spring", bounce: 0, duration: 0.3 }}
              className="fixed inset-y-0 left-0 w-64 bg-[#0A0F1A] border-r border-divider z-50 md:hidden shadow-2xl"
            >
              <Sidebar 
                onClose={() => setMobileMenuOpen(false)} 
                onClearSession={() => {
                  onClearSession();
                  setMobileMenuOpen(false);
                }} 
                sessions={sessions}
                sessionId={sessionId}
                onLoadSession={onLoadSession}
                onDeleteSession={onDeleteSession}
              />
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 relative">
        <TopBar 
          hazardType={hazardType} 
          onClearSession={onClearSession} 
          onMenuClick={() => setMobileMenuOpen(true)} 
        />
        
        <MessageFeed 
          messages={messages} 
          isGenerating={isGenerating} 
        />
        
        <MessageInput onSendMessage={onSendMessage} />
      </div>
    </div>
  );
};

export default ChatLayout;
