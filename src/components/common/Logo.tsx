interface LogoProps {
  compact?: boolean;
}

function ChariotIcon({ size = 32 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 40 40"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <defs>
        <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
          <feDropShadow dx="0.5" dy="0.5" stdDeviation="0.5" floodColor="#333" floodOpacity="0.3"/>
        </filter>
      </defs>
      
      {/* Bold rounded square background */}
      <rect x="0" y="0" width="40" height="40" rx="8" fill="#FF6600"/>
      
      {/* Chariot silhouette - black and bold */}
      <g transform="translate(4, 4) scale(0.8)" filter="url(#shadow)">
        {/* Front wheel */}
        <circle cx="12" cy="28" r="5" stroke="#1A1A1A" strokeWidth="2.5" fill="none"/>
        <circle cx="12" cy="28" r="2" fill="#1A1A1A"/>
        
        {/* Rear wheel */}
        <circle cx="28" cy="28" r="5" stroke="#1A1A1A" strokeWidth="2.5" fill="none"/>
        <circle cx="28" cy="28" r="2" fill="#1A1A1A"/>
        
        {/* Axle */}
        <path d="M12 28H28" stroke="#1A1A1A" strokeWidth="2.5" strokeLinecap="round"/>
        
        {/* Chariot body */}
        <path d="M8 20C8 20 5 20 5 23C5 26 8 27 8 27" stroke="#1A1A1A" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" fill="none"/>
        <path d="M8 20H32C34 20 35 18 35 16V12C35 10 34 9 32 9H22" stroke="#1A1A1A" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" fill="none"/>
        <path d="M22 9C18 9 12 10 8 14C4 18 8 20 8 20" stroke="#1A1A1A" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" fill="none"/>
        
        {/* Canopy */}
        <path d="M18 9V6C18 5 19 4 20 4H30C31 4 32 5 32 6V9" stroke="#1A1A1A" strokeWidth="2.5" strokeLinecap="round" fill="none"/>
        
        {/* Flag */}
        <path d="M34 4V8" stroke="#1A1A1A" strokeWidth="2.5" strokeLinecap="round"/>
        <path d="M34 4L38 5.5L34 7" stroke="#1A1A1A" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" fill="none"/>
        
        {/* Horse reins */}
        <path d="M35 14L38 11" stroke="#1A1A1A" strokeWidth="2.5" strokeLinecap="round"/>
      </g>
    </svg>
  );
}

export function Logo({ compact = false }: LogoProps) {
  const brandColor = '#FF6600';
  
  return (
    <div className={`brand ${compact ? 'brand--compact' : ''}`} aria-label="Sprint Sarthi" style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
      <span className="brand__mark" aria-hidden="true" style={{ color: brandColor }}>
        <ChariotIcon size={36} />
      </span>
      {!compact && (
        <span className="brand__copy" style={{ 
          display: 'flex', 
          flexDirection: 'column', 
          justifyContent: 'center',
          lineHeight: 1.1,
          gap: '1px'
        }}>
          <strong style={{ 
            fontFamily: "'Poppins', sans-serif",
            fontWeight: 700, 
            color: brandColor, 
            fontSize: '17px',
            letterSpacing: '-0.3px'
          }}>Sprint Sarthi</strong>
          <small style={{ 
            fontFamily: "'Poppins', sans-serif",
            fontWeight: 600, 
            color: brandColor, 
            fontSize: '9px',
            letterSpacing: '2.5px',
            textTransform: 'uppercase'
          }}>AI Assistant</small>
        </span>
      )}
    </div>
  );
}
