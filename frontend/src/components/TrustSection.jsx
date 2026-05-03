import React from 'react';
import { Shield, Cpu, Zap, AlertTriangle, LayoutGrid, Globe } from 'lucide-react';

const FEATURES = [
  {
    icon: <Shield className="w-5 h-5 text-muted" />,
    title: "Government Verified Sources",
    description: "All responses are grounded in NDMA, IMD, NDRF, and State Disaster Management Authority guidelines — not internet data."
  },
  {
    icon: <Cpu className="w-5 h-5 text-muted" />,
    title: "FastAPI + RAG Architecture",
    description: "Retrieval-Augmented Generation ensures answers are factually anchored to real documents, not hallucinated."
  },
  {
    icon: <Zap className="w-5 h-5 text-muted" />,
    title: "Real-Time Hazard Classification",
    description: "ARIA automatically identifies flood, cyclone, heatwave, earthquake, or drought context from your question — no tagging needed."
  },
  {
    icon: <AlertTriangle className="w-5 h-5 text-muted" />,
    title: "Emergency-First Response Design",
    description: "Every UI element is optimized for high-stress, fast-decision scenarios. Clarity is the first feature."
  },
  {
    icon: <LayoutGrid className="w-5 h-5 text-muted" />,
    title: "Dual Response Intelligence",
    description: "Preparedness mode delivers structured action checklists. Information mode delivers clear contextual explanations."
  },
  {
    icon: <Globe className="w-5 h-5 text-muted" />,
    title: "India-Specific Disaster Context",
    description: "Trained on Indian geographic, climatic, and institutional data. Designed for the 1.4 billion most disaster-exposed people on Earth."
  }
];

const TrustSection = () => {
  return (
    <section className="w-full bg-background py-24 px-6 md:px-12 lg:px-24 flex flex-col items-center border-t border-divider z-20 relative">
      
      {/* Header */}
      <div className="w-full max-w-5xl flex flex-col items-center text-center gap-4 mb-16">
        <span className="font-mono text-xs text-muted uppercase tracking-widest">
          WHY TRUST ARIA
        </span>
        <h2 className="text-3xl md:text-4xl font-syne font-bold text-heading max-w-2xl leading-tight">
          Built on Government Intelligence.<br />
          <span className="text-muted">Designed for Real Emergencies.</span>
        </h2>
      </div>

      {/* Feature Grid */}
      <div className="w-full max-w-5xl grid grid-cols-1 md:grid-cols-2 gap-x-12 gap-y-10 mb-20">
        {FEATURES.map((feature, idx) => (
          <div key={idx} className="flex gap-4">
            <div className="shrink-0 w-10 h-10 rounded-lg bg-surface border border-divider flex items-center justify-center">
              {feature.icon}
            </div>
            <div className="flex flex-col gap-1.5 mt-1">
              <h3 className="font-heading font-medium text-heading text-[16px]">
                {feature.title}
              </h3>
              <p className="font-body text-[15px] leading-relaxed text-muted">
                {feature.description}
              </p>
            </div>
          </div>
        ))}
      </div>

      {/* Logos Bottom Bar */}
      <div className="w-full max-w-4xl flex flex-col items-center gap-6 pt-12 border-t border-divider">
        <span className="font-mono text-[10px] text-muted opacity-60 uppercase tracking-widest">
          Intelligence Sourced From
        </span>
        <div className="flex flex-wrap justify-center gap-x-12 gap-y-6 opacity-40 grayscale">
          {/* Using text representations as logo placeholders, styled institutionally */}
          <span className="font-heading font-bold text-lg text-body tracking-wider">NDMA</span>
          <span className="font-heading font-bold text-lg text-body tracking-wider">IMD</span>
          <span className="font-heading font-bold text-lg text-body tracking-wider">NDRF</span>
          <span className="font-heading font-bold text-lg text-body tracking-wider">STATE DMA</span>
        </div>
      </div>
    </section>
  );
};

export default TrustSection;
