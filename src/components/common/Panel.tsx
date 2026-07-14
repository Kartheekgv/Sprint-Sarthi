import type { HTMLAttributes, ReactNode } from 'react';

interface PanelProps extends HTMLAttributes<HTMLElement> {
  title?: string;
  description?: string;
  eyebrow?: string;
  action?: ReactNode;
  children: ReactNode;
  padding?: 'none' | 'sm' | 'md';
}

export function Panel({
  title,
  description,
  eyebrow,
  action,
  children,
  padding = 'md',
  className = '',
  ...props
}: PanelProps) {
  return (
    <section className={`panel panel--padding-${padding} ${className}`.trim()} {...props}>
      {title || description || eyebrow || action ? (
        <header className="panel__header">
          <div className="panel__heading">
            {eyebrow ? <span className="panel__eyebrow">{eyebrow}</span> : null}
            {title ? <h2>{title}</h2> : null}
            {description ? <p>{description}</p> : null}
          </div>
          {action ? <div className="panel__action">{action}</div> : null}
        </header>
      ) : null}
      <div className="panel__body">{children}</div>
    </section>
  );
}
