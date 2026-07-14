import { Bot, Sparkles } from 'lucide-react';

interface LogoProps {
  compact?: boolean;
}

export function Logo({ compact = false }: LogoProps) {
  return (
    <div className={`brand ${compact ? 'brand--compact' : ''}`} aria-label="Sprint Sarthi">
      <span className="brand__mark" aria-hidden="true">
        <Bot size={24} strokeWidth={2.1} />
        <Sparkles className="brand__spark" size={10} strokeWidth={2.5} />
      </span>
      {!compact && (
        <span className="brand__copy">
          <strong>Sprint Sarthi</strong>
          <small>AI sprint assistant</small>
        </span>
      )}
    </div>
  );
}
