import React from 'react';
import { Droplets, Sun, Wind, Activity, Phone, BriefcaseMedical } from 'lucide-react';

const ACTION_CARDS = [
  {
    id: 'flood',
    title: 'Flood Safety Protocol',
    description: 'Step-by-step actions before, during, and after flooding',
    icon: <Droplets className="w-5 h-5 opacity-70 group-hover:opacity-100 transition-opacity" />,
    hoverBorder: '#00B4D8'
  },
  {
    id: 'heatwave',
    title: 'Heatwave Preparation',
    description: 'Stay safe during extreme heat events',
    icon: <Sun className="w-5 h-5 opacity-70 group-hover:opacity-100 transition-opacity" />,
    hoverBorder: '#EF4444'
  },
  {
    id: 'cyclone',
    title: 'Cyclone Emergency Checklist',
    description: 'Complete cyclone readiness and evacuation plan',
    icon: <Wind className="w-5 h-5 opacity-70 group-hover:opacity-100 transition-opacity" />,
    hoverBorder: '#F59E0B'
  },
  {
    id: 'earthquake',
    title: 'Earthquake Survival Guide',
    description: 'What to do when the ground shakes',
    icon: <Activity className="w-5 h-5 opacity-70 group-hover:opacity-100 transition-opacity" />,
    hoverBorder: '#B07D62'
  },
  {
    id: 'contacts',
    title: 'Emergency Contact Guide',
    description: 'NDRF, SDRF, and state disaster helpline numbers',
    icon: <Phone className="w-5 h-5 opacity-70 group-hover:opacity-100 transition-opacity" />,
    hoverBorder: '#6366F1'
  },
  {
    id: 'kit',
    title: 'Disaster Preparedness Kit',
    description: 'Build your 72-hour emergency go-bag',
    icon: <BriefcaseMedical className="w-5 h-5 opacity-70 group-hover:opacity-100 transition-opacity" />,
    hoverBorder: '#6366F1'
  }
];

const QuickActionGrid = ({ onActionClick }) => {
  return (
    <div className="w-full mt-16 z-20 relative">
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        {ACTION_CARDS.map((card) => (
          <button
            key={card.id}
            onClick={() => onActionClick(card.title)}
            className="group relative glass-panel text-left p-4 rounded-xl flex items-start gap-4 hover:-translate-y-0.5 hover:shadow-card transition-all duration-150 overflow-hidden"
          >
            {/* Hover border effect */}
            <div 
              className="absolute left-0 top-0 bottom-0 w-1 opacity-0 group-hover:opacity-100 transition-opacity duration-150"
              style={{ backgroundColor: card.hoverBorder }}
            />
            
            <div className="mt-1 shrink-0 text-muted group-hover:text-body transition-colors">
              {card.icon}
            </div>
            
            <div className="flex flex-col gap-1">
              <span className="font-heading font-medium text-[15px] text-heading leading-tight">
                {card.title}
              </span>
              <span className="font-body text-xs text-muted leading-relaxed">
                {card.description}
              </span>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
};

export default QuickActionGrid;
