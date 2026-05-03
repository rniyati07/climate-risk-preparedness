import React, { useState } from 'react';
import HeroSection from './components/HeroSection';
import TrustSection from './components/TrustSection';
import ChatLayout from './components/ChatLayout';
import { AnimatePresence, motion } from 'framer-motion';

/**
 * Parse the raw markdown answer from the backend into structured phase objects.
 * 
 * The LLM outputs headers like:
 *   ## 🔴 Before
 *   ## 🟡 During  
 *   ## 🟢 After
 *   ## 🏥 Health Safety
 *   ## 📚 Sources
 * 
 * Everything under each header (bullets, numbered lists, plain text) belongs to that phase.
 * The Sources section is stripped out (we already have citations from the backend).
 */
const parsePreparednessPhases = (markdown) => {
  if (!markdown || typeof markdown !== 'string') {
    return [{ type: 'BEFORE', items: ['No response content available.'] }];
  }

  const lines = markdown.split('\n');
  const phases = [];
  let currentPhase = null;
  let skipSection = false; // to skip the ## Sources section

  const classifyHeader = (headerText) => {
    const upper = headerText.toUpperCase();
    if (upper.includes('SOURCE') || upper.includes('📚')) return '__SKIP__';
    if (upper.includes('DURING') || upper.includes('ACTIVE') || upper.includes('🟡')) return 'DURING';
    if (upper.includes('AFTER') || upper.includes('RECOVERY') || upper.includes('🟢')) return 'AFTER';
    if (upper.includes('HEALTH') || upper.includes('MEDICAL') || upper.includes('🏥')) return 'HEALTH';
    if (upper.includes('BEFORE') || upper.includes('PRE') || upper.includes('🔴')) return 'BEFORE';
    // If it doesn't match any known phase, treat it as a generic BEFORE section
    return 'BEFORE';
  };

  lines.forEach(line => {
    const trimmed = line.trim();

    // Detect markdown headers (## or ###)
    if (/^#{1,3}\s+/.test(trimmed)) {
      const headerText = trimmed.replace(/^#+\s*/, '');
      const phaseType = classifyHeader(headerText);

      if (phaseType === '__SKIP__') {
        skipSection = true;
        return;
      }

      skipSection = false;
      currentPhase = { type: phaseType, items: [] };
      phases.push(currentPhase);
      return;
    }

    // If we're in the sources section, skip everything
    if (skipSection) return;

    // Skip empty lines
    if (!trimmed) return;

    // If no phase header has been encountered yet, we just ignore the text
    // (the prompt strictly forbids text before the first header)
    if (!currentPhase) return;

    // Parse bullet items: - item, * item, or numbered: 1. item, 2) item
    if (/^[-*]\s+/.test(trimmed)) {
      currentPhase.items.push(trimmed.replace(/^[-*]\s+/, ''));
    } else if (/^\d+[.)]\s+/.test(trimmed)) {
      currentPhase.items.push(trimmed.replace(/^\d+[.)]\s+/, ''));
    } else {
      // Plain text paragraph — include it as an item too
      currentPhase.items.push(trimmed);
    }
  });

  // Filter out phases with no items
  const validPhases = phases.filter(p => p.items.length > 0);
  return validPhases;
};

function App() {
  const [view, setView] = useState('hero'); // 'hero' | 'chat'
  const [hazardType, setHazardType] = useState(null);
  const [messages, setMessages] = useState([]);
  const [isGenerating, setIsGenerating] = useState(false);
  
  // Session Management State
  const [sessionId, setSessionId] = useState(() => Date.now().toString());
  const [sessions, setSessions] = useState([]);

  // Load sidebar sessions from localStorage
  const refreshSessions = () => {
    const keys = Object.keys(localStorage).filter(k => k.startsWith('aria_session_'));
    let loaded = keys.map(k => JSON.parse(localStorage.getItem(k)));
    loaded.sort((a, b) => b.updatedAt - a.updatedAt); // newest first
    setSessions(loaded);
  };

  // Initial load
  React.useEffect(() => {
    refreshSessions();
  }, []);

  // Save current session on every update
  React.useEffect(() => {
    if (messages.length === 0) return;

    const title = messages.find(m => m.role === 'user')?.content.substring(0, 40) || 'New Chat';
    
    const sessionData = {
      id: sessionId,
      title: title.length === 40 ? title + '...' : title,
      hazard: hazardType || 'general',
      messages,
      createdAt: parseInt(sessionId),
      updatedAt: Date.now()
    };

    localStorage.setItem(`aria_session_${sessionId}`, JSON.stringify(sessionData));
    
    // Enforce storage limit (max 5)
    const keys = Object.keys(localStorage).filter(k => k.startsWith('aria_session_'));
    if (keys.length > 5) {
      let loaded = keys.map(k => JSON.parse(localStorage.getItem(k)));
      loaded.sort((a, b) => a.updatedAt - b.updatedAt); // oldest first
      while (loaded.length > 5) {
        const oldest = loaded.shift();
        localStorage.removeItem(`aria_session_${oldest.id}`);
      }
    }

    refreshSessions();
  }, [messages, hazardType, sessionId]);

  const handleLoadSession = (id) => {
    const data = JSON.parse(localStorage.getItem(`aria_session_${id}`));
    if (data) {
      setSessionId(data.id);
      setMessages(data.messages);
      setHazardType(data.hazard);
      setView('chat');
    }
  };

  const handleDeleteSession = (id) => {
    localStorage.removeItem(`aria_session_${id}`);
    if (id === sessionId) {
      handleClearSession();
    } else {
      refreshSessions();
    }
  };

  const handleStartChat = (initialMessage) => {
    setView('chat');
    if (initialMessage && typeof initialMessage === 'string') {
      handleSendMessage(initialMessage);
    }
  };

  const handleSendMessage = async (text) => {
    // Add user message
    const userMsg = { role: 'user', content: text };
    setMessages(prev => [...prev, userMsg]);
    setIsGenerating(true);

    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/query`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ question: text })
      });

      if (!response.ok) {
        throw new Error(`API returned status ${response.status}`);
      }

      const data = await response.json();

      // ── Hazard theme (from backend risk_context) ───────
      const detectedHazard = data.risk_context?.hazard?.toLowerCase() || 'general';
      setHazardType(detectedHazard);

      // ── Citations ──────────────────────────────────────
      const citations = (data.sources || []).map(s => `${s.source}, p.${s.page}`);

      // ── Metadata ───────────────────────────────────────
      const rawConfidence = data.risk_context?.confidence;
      const metadata = {
        hazard: data.risk_context?.hazard || 'Unknown',
        intent: data.risk_context?.intent || 'Information',
        confidence: rawConfidence != null ? Math.round(rawConfidence * 100) : null,
        time: `${data.elapsed_seconds || 0}s`,
        sources: data.sources?.length || 0
      };

      // ── Mode switch (from backend intent) ──────────────
      const intentLower = (data.risk_context?.intent || '').toLowerCase();
      let isPreparedness = false;
      
      // SAFETY CHECK: If hazard is general, NEVER use preparedness mode phase cards.
      // Only render phase cards if ALL conditions are true:
      if (intentLower === 'preparedness' && detectedHazard !== 'general') {
        // Check if the answer actually contains phase headers
        if (/##\s*(🔴|🟡|🟢|🏥)?\s*(Before|During|After|Health|Pre|Active|Recovery|Medical)/i.test(data.answer)) {
          isPreparedness = true;
        }
      }

      const responseMsg = {
        role: 'aria',
        mode: isPreparedness ? 'preparedness' : 'information',
        citations,
        metadata
      };

      if (isPreparedness) {
        responseMsg.phases = parsePreparednessPhases(data.answer);
      } else {
        responseMsg.content = data.answer;
      }

      setMessages(prev => [...prev, responseMsg]);
    } catch (error) {
      console.error("Failed to fetch from backend:", error);
      setMessages(prev => [...prev, {
        role: 'aria',
        mode: 'information',
        content: `**Error:** Could not connect to the backend API. Please ensure the server is running at ${import.meta.env.VITE_API_URL || 'http://localhost:8000'}.\n\nDetails: ${error.message}`,
        citations: [],
        metadata: { hazard: 'error', intent: 'system' }
      }]);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleClearSession = () => {
    setMessages([]);
    setHazardType(null);
    setSessionId(Date.now().toString());
  };

  return (
    <div className={`min-h-screen w-full bg-background text-body font-body antialiased ${hazardType ? `hazard-${hazardType}` : ''} hazard-transition`}>
      <AnimatePresence mode="wait">
        {view === 'hero' ? (
          <motion.div
            key="hero"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.5 }}
            className="flex flex-col"
          >
            <HeroSection onStartChat={handleStartChat} />
            <TrustSection />
          </motion.div>
        ) : (
          <motion.div
            key="chat"
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.4 }}
            className="h-screen w-full"
          >
            <ChatLayout
              hazardType={hazardType}
              messages={messages}
              isGenerating={isGenerating}
              onSendMessage={handleSendMessage}
              onClearSession={handleClearSession}
              sessions={sessions}
              sessionId={sessionId}
              onLoadSession={handleLoadSession}
              onDeleteSession={handleDeleteSession}
            />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default App;
