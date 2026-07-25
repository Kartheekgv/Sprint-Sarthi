// Large decorative SVG illustrations for the dashboard

// Rocket/Sprint illustration - for WelcomeHero
export function RocketIllustration({ className = '' }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 200 200"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      {/* Rocket body */}
      <path
        d="M100 20C100 20 130 50 130 100C130 150 100 180 100 180C100 180 70 150 70 100C70 50 100 20 100 20Z"
        fill="url(#rocketGradient)"
        stroke="#FF6600"
        strokeWidth="2"
      />
      {/* Rocket window */}
      <circle cx="100" cy="80" r="15" fill="#1A1A1A" stroke="#FF6600" strokeWidth="2" />
      <circle cx="100" cy="80" r="8" fill="#FF6600" opacity="0.3" />
      {/* Rocket fins */}
      <path
        d="M70 120L50 150L70 140Z"
        fill="#FF6600"
        opacity="0.8"
      />
      <path
        d="M130 120L150 150L130 140Z"
        fill="#FF6600"
        opacity="0.8"
      />
      {/* Rocket flame */}
      <ellipse cx="100" cy="185" rx="15" ry="10" fill="#FF6600" opacity="0.6">
        <animate attributeName="ry" values="10;15;10" dur="0.5s" repeatCount="indefinite" />
        <animate attributeName="opacity" values="0.6;0.9;0.6" dur="0.5s" repeatCount="indefinite" />
      </ellipse>
      <ellipse cx="100" cy="185" rx="8" ry="6" fill="#FFB366">
        <animate attributeName="ry" values="6;10;6" dur="0.4s" repeatCount="indefinite" />
      </ellipse>
      {/* Stars */}
      <circle cx="40" cy="40" r="2" fill="#FF6600" opacity="0.5">
        <animate attributeName="opacity" values="0.5;1;0.5" dur="2s" repeatCount="indefinite" />
      </circle>
      <circle cx="160" cy="60" r="2" fill="#FF6600" opacity="0.5">
        <animate attributeName="opacity" values="0.5;1;0.5" dur="2.5s" repeatCount="indefinite" />
      </circle>
      <circle cx="30" cy="100" r="1.5" fill="#FF6600" opacity="0.4">
        <animate attributeName="opacity" values="0.4;0.8;0.4" dur="3s" repeatCount="indefinite" />
      </circle>
      <circle cx="170" cy="120" r="1.5" fill="#FF6600" opacity="0.4">
        <animate attributeName="opacity" values="0.4;0.8;0.4" dur="2.2s" repeatCount="indefinite" />
      </circle>
      <defs>
        <linearGradient id="rocketGradient" x1="100" y1="20" x2="100" y2="180" gradientUnits="userSpaceOnUse">
          <stop stopColor="#FF8533" />
          <stop offset="1" stopColor="#FF6600" />
        </linearGradient>
      </defs>
    </svg>
  );
}

// Analytics/Chart illustration - for stats area
export function AnalyticsIllustration({ className = '' }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 200 160"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      {/* Chart bars */}
      <rect x="20" y="100" width="25" height="50" rx="4" fill="#FF6600" opacity="0.3">
        <animate attributeName="height" values="50;60;50" dur="2s" repeatCount="indefinite" />
        <animate attributeName="y" values="100;90;100" dur="2s" repeatCount="indefinite" />
      </rect>
      <rect x="55" y="70" width="25" height="80" rx="4" fill="#FF6600" opacity="0.5">
        <animate attributeName="height" values="80;90;80" dur="2.5s" repeatCount="indefinite" />
        <animate attributeName="y" values="70;60;70" dur="2.5s" repeatCount="indefinite" />
      </rect>
      <rect x="90" y="50" width="25" height="100" rx="4" fill="#FF6600" opacity="0.7">
        <animate attributeName="height" values="100;110;100" dur="3s" repeatCount="indefinite" />
        <animate attributeName="y" values="50;40;50" dur="3s" repeatCount="indefinite" />
      </rect>
      <rect x="125" y="30" width="25" height="120" rx="4" fill="#FF6600" opacity="0.85">
        <animate attributeName="height" values="120;130;120" dur="2.2s" repeatCount="indefinite" />
        <animate attributeName="y" values="30;20;30" dur="2.2s" repeatCount="indefinite" />
      </rect>
      <rect x="160" y="20" width="25" height="130" rx="4" fill="#FF6600">
        <animate attributeName="height" values="130;140;130" dur="2.8s" repeatCount="indefinite" />
        <animate attributeName="y" values="20;10;20" dur="2.8s" repeatCount="indefinite" />
      </rect>
      {/* Trend line */}
      <path
        d="M32 95 L67 65 L102 45 L137 25 L172 15"
        stroke="#FFB366"
        strokeWidth="3"
        strokeLinecap="round"
        fill="none"
        strokeDasharray="5,5"
      >
        <animate attributeName="stroke-dashoffset" values="0;10;0" dur="1s" repeatCount="indefinite" />
      </path>
      {/* Data points */}
      <circle cx="32" cy="95" r="5" fill="#FF6600" />
      <circle cx="67" cy="65" r="5" fill="#FF6600" />
      <circle cx="102" cy="45" r="5" fill="#FF6600" />
      <circle cx="137" cy="25" r="5" fill="#FF6600" />
      <circle cx="172" cy="15" r="5" fill="#FF6600" />
    </svg>
  );
}

// Team collaboration illustration
export function TeamIllustration({ className = '' }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 200 120"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      {/* Person 1 */}
      <circle cx="50" cy="35" r="18" fill="#FF6600" opacity="0.8" />
      <circle cx="50" cy="30" r="10" fill="#1A1A1A" />
      <rect x="35" y="55" width="30" height="40" rx="8" fill="#FF6600" opacity="0.6" />
      
      {/* Person 2 (center, larger) */}
      <circle cx="100" cy="30" r="22" fill="#FF6600" />
      <circle cx="100" cy="24" r="12" fill="#1A1A1A" />
      <rect x="82" y="52" width="36" height="48" rx="10" fill="#FF6600" opacity="0.8" />
      
      {/* Person 3 */}
      <circle cx="150" cy="35" r="18" fill="#FF6600" opacity="0.8" />
      <circle cx="150" cy="30" r="10" fill="#1A1A1A" />
      <rect x="135" y="55" width="30" height="40" rx="8" fill="#FF6600" opacity="0.6" />
      
      {/* Connection lines */}
      <path
        d="M68 50 Q85 35 95 45"
        stroke="#FFB366"
        strokeWidth="2"
        fill="none"
        opacity="0.5"
      >
        <animate attributeName="opacity" values="0.5;1;0.5" dur="2s" repeatCount="indefinite" />
      </path>
      <path
        d="M132 50 Q115 35 105 45"
        stroke="#FFB366"
        strokeWidth="2"
        fill="none"
        opacity="0.5"
      >
        <animate attributeName="opacity" values="0.5;1;0.5" dur="2.3s" repeatCount="indefinite" />
      </path>
      
      {/* Floating elements */}
      <rect x="25" cy="15" width="10" height="8" rx="2" fill="#FF6600" opacity="0.3">
        <animate attributeName="y" values="15;10;15" dur="3s" repeatCount="indefinite" />
      </rect>
      <rect x="165" cy="15" width="10" height="8" rx="2" fill="#FF6600" opacity="0.3">
        <animate attributeName="y" values="15;10;15" dur="3.5s" repeatCount="indefinite" />
      </rect>
    </svg>
  );
}

// Sprint board/Kanban illustration
export function KanbanIllustration({ className = '' }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 200 150"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      {/* Board columns */}
      <rect x="10" y="20" width="55" height="120" rx="8" fill="#FF6600" opacity="0.1" stroke="#FF6600" strokeWidth="1" opacity="0.3" />
      <rect x="72" y="20" width="55" height="120" rx="8" fill="#FF6600" opacity="0.15" stroke="#FF6600" strokeWidth="1" opacity="0.4" />
      <rect x="134" y="20" width="55" height="120" rx="8" fill="#FF6600" opacity="0.2" stroke="#FF6600" strokeWidth="1" opacity="0.5" />
      
      {/* Column headers */}
      <text x="37" y="38" fill="#FF6600" fontSize="10" fontWeight="600" textAnchor="middle">TO DO</text>
      <text x="100" y="38" fill="#FF6600" fontSize="10" fontWeight="600" textAnchor="middle">IN PROGRESS</text>
      <text x="162" y="38" fill="#FF6600" fontSize="10" fontWeight="600" textAnchor="middle">DONE</text>
      
      {/* Cards in TO DO */}
      <rect x="16" y="48" width="43" height="25" rx="4" fill="#FF6600" opacity="0.4" />
      <rect x="16" y="78" width="43" height="25" rx="4" fill="#FF6600" opacity="0.3" />
      <rect x="16" y="108" width="43" height="25" rx="4" fill="#FF6600" opacity="0.2" />
      
      {/* Cards in IN PROGRESS - with animation */}
      <rect x="78" y="48" width="43" height="25" rx="4" fill="#FF6600" opacity="0.6">
        <animate attributeName="opacity" values="0.6;0.8;0.6" dur="2s" repeatCount="indefinite" />
      </rect>
      <rect x="78" y="78" width="43" height="25" rx="4" fill="#FF6600" opacity="0.5">
        <animate attributeName="opacity" values="0.5;0.7;0.5" dur="2.5s" repeatCount="indefinite" />
      </rect>
      
      {/* Cards in DONE */}
      <rect x="140" y="48" width="43" height="25" rx="4" fill="#FF6600" opacity="0.8" />
      <rect x="140" y="78" width="43" height="25" rx="4" fill="#FF6600" opacity="0.7" />
      <rect x="140" y="108" width="43" height="25" rx="4" fill="#FF6600" opacity="0.6" />
      
      {/* Checkmarks on done cards */}
      <path d="M156 58 L160 62 L168 54" stroke="#1A1A1A" strokeWidth="2" strokeLinecap="round" />
      <path d="M156 88 L160 92 L168 84" stroke="#1A1A1A" strokeWidth="2" strokeLinecap="round" />
      <path d="M156 118 L160 122 L168 114" stroke="#1A1A1A" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

// Gear/Settings illustration for AI section
export function AIBrainIllustration({ className = '' }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 120 120"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      {/* Brain outline */}
      <path
        d="M60 20C40 20 25 35 25 55C25 65 30 75 40 80L40 95C40 98 43 100 46 100L74 100C77 100 80 98 80 95L80 80C90 75 95 65 95 55C95 35 80 20 60 20Z"
        fill="url(#brainGradient)"
        stroke="#FF6600"
        strokeWidth="2"
      />
      {/* Neural connections */}
      <circle cx="45" cy="45" r="6" fill="#1A1A1A" />
      <circle cx="60" cy="40" r="6" fill="#1A1A1A" />
      <circle cx="75" cy="45" r="6" fill="#1A1A1A" />
      <circle cx="50" cy="60" r="6" fill="#1A1A1A" />
      <circle cx="70" cy="60" r="6" fill="#1A1A1A" />
      <circle cx="60" cy="75" r="6" fill="#1A1A1A" />
      
      {/* Connections */}
      <line x1="45" y1="45" x2="60" y2="40" stroke="#FFB366" strokeWidth="2" opacity="0.6">
        <animate attributeName="opacity" values="0.6;1;0.6" dur="1.5s" repeatCount="indefinite" />
      </line>
      <line x1="60" y1="40" x2="75" y2="45" stroke="#FFB366" strokeWidth="2" opacity="0.6">
        <animate attributeName="opacity" values="0.6;1;0.6" dur="1.8s" repeatCount="indefinite" />
      </line>
      <line x1="45" y1="45" x2="50" y2="60" stroke="#FFB366" strokeWidth="2" opacity="0.6">
        <animate attributeName="opacity" values="0.6;1;0.6" dur="2s" repeatCount="indefinite" />
      </line>
      <line x1="75" y1="45" x2="70" y2="60" stroke="#FFB366" strokeWidth="2" opacity="0.6">
        <animate attributeName="opacity" values="0.6;1;0.6" dur="1.7s" repeatCount="indefinite" />
      </line>
      <line x1="50" y1="60" x2="60" y2="75" stroke="#FFB366" strokeWidth="2" opacity="0.6">
        <animate attributeName="opacity" values="0.6;1;0.6" dur="2.2s" repeatCount="indefinite" />
      </line>
      <line x1="70" y1="60" x2="60" y2="75" stroke="#FFB366" strokeWidth="2" opacity="0.6">
        <animate attributeName="opacity" values="0.6;1;0.6" dur="1.9s" repeatCount="indefinite" />
      </line>
      <line x1="50" y1="60" x2="70" y2="60" stroke="#FFB366" strokeWidth="2" opacity="0.6">
        <animate attributeName="opacity" values="0.6;1;0.6" dur="2.1s" repeatCount="indefinite" />
      </line>
      
      {/* Pulse rings */}
      <circle cx="60" cy="55" r="25" stroke="#FF6600" strokeWidth="1" fill="none" opacity="0.3">
        <animate attributeName="r" values="25;35;25" dur="3s" repeatCount="indefinite" />
        <animate attributeName="opacity" values="0.3;0;0.3" dur="3s" repeatCount="indefinite" />
      </circle>
      
      <defs>
        <linearGradient id="brainGradient" x1="60" y1="20" x2="60" y2="100" gradientUnits="userSpaceOnUse">
          <stop stopColor="#FF8533" opacity="0.3" />
          <stop offset="1" stopColor="#FF6600" opacity="0.5" />
        </linearGradient>
      </defs>
    </svg>
  );
}
