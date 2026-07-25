import { ArrowRight, CalendarDays, CircleCheckBig, Plus, Sparkles } from 'lucide-react';
import { Button } from '../common/Button';
import { RocketIllustration } from '../common/DashboardIllustrations';

interface WelcomeHeroProps {
  project: string;
  onOpenPlanning: () => void;
  onNewSprint: () => void;
}

export function WelcomeHero({ project, onOpenPlanning, onNewSprint }: WelcomeHeroProps) {
  return (
    <section className="welcome-hero">
      <RocketIllustration className="welcome-hero__illustration" />
      <div className="welcome-hero__copy">
        <div className="welcome-hero__eyebrow">
          <span className="live-dot" />
          Sprint 24 is active
        </div>
        <h1>Good morning, Kartheek.</h1>
        <p>
          <strong>{project}</strong> is on track. Resolve two planning risks today to keep the sprint predictable.
        </p>
        <div className="welcome-hero__actions">
          <Button variant="primary" onClick={onOpenPlanning} trailingIcon={<ArrowRight size={17} />}>
            Review sprint plan
          </Button>
          <Button onClick={onNewSprint} icon={<Plus size={17} />}>
            New sprint
          </Button>
        </div>
      </div>

      <div className="welcome-hero__summary">
        <div className="hero-summary__topline">
          <span>
            <CalendarDays size={16} /> 14-25 July
          </span>
          <span className="health-pill">
            <CircleCheckBig size={15} /> Healthy
          </span>
        </div>
        <div className="hero-summary__metric">
          <div>
            <small>Sprint goal progress</small>
            <strong>68%</strong>
          </div>
          <span className="hero-summary__spark">
            <Sparkles size={22} />
          </span>
        </div>
        <div className="hero-summary__progress">
          <span style={{ width: '68%' }} />
        </div>
        <div className="hero-summary__footer">
          <span>26 of 38 story points complete</span>
          <strong>8 days left</strong>
        </div>
      </div>
    </section>
  );
}
