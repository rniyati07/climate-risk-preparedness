import React, { useMemo } from 'react';

export const InformationMarkdown = ({ content }) => {
  // A simple line-by-line parser for the raw markdown string
  const blocks = useMemo(() => {
    if (typeof content !== 'string') return [];
    
    const lines = content.split('\n');
    const parsedBlocks = [];
    let currentList = null;

    lines.forEach(line => {
      const trimmed = line.trim();
      if (!trimmed) {
        if (currentList) {
          parsedBlocks.push(currentList);
          currentList = null;
        }
        return;
      }

      if (trimmed.startsWith('## ')) {
        if (currentList) { parsedBlocks.push(currentList); currentList = null; }
        parsedBlocks.push({ type: 'h2', text: trimmed.substring(3).trim() });
      } else if (trimmed.startsWith('### ')) {
        if (currentList) { parsedBlocks.push(currentList); currentList = null; }
        parsedBlocks.push({ type: 'h3', text: trimmed.substring(4).trim() });
      } else if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
        if (!currentList) currentList = { type: 'ul', items: [] };
        currentList.items.push(trimmed.substring(2).trim());
      } else {
        if (currentList) { parsedBlocks.push(currentList); currentList = null; }
        parsedBlocks.push({ type: 'p', text: trimmed });
      }
    });

    if (currentList) {
      parsedBlocks.push(currentList);
    }

    return parsedBlocks;
  }, [content]);
  
  return (
    <div className="flex flex-col gap-3 text-body font-body text-[13px] leading-[1.7]">
      {blocks.map((block, idx) => {
        if (block.type === 'h2') {
          return <h2 key={idx} className="font-body font-semibold text-[15px] text-[var(--accent)] mt-2">{block.text}</h2>;
        }
        if (block.type === 'h3') {
          return <h3 key={idx} className="font-body font-medium text-[13px] text-heading uppercase tracking-wider mt-1">{block.text}</h3>;
        }
        if (block.type === 'p') {
          return (
            <p key={idx} dangerouslySetInnerHTML={{ __html: block.text.replace(/\*\*(.*?)\*\*/g, '<strong class="font-bold text-[#F0F4FF]">$1</strong>') }} />
          );
        }
        if (block.type === 'ul') {
          return (
            <ul key={idx} className="flex flex-col gap-2 ml-1">
              {block.items.map((item, i) => (
                <li key={i} className="flex items-start gap-2.5">
                  <div className="mt-2 shrink-0 w-1 h-1 bg-[var(--accent)] rounded-sm" />
                  <span dangerouslySetInnerHTML={{ __html: item.replace(/\*\*(.*?)\*\*/g, '<strong class="font-bold text-[#F0F4FF]">$1</strong>') }} />
                </li>
              ))}
            </ul>
          );
        }
        return null;
      })}
    </div>
  );
};
