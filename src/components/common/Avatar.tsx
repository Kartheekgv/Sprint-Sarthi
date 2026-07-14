import { initials } from '../../utils/formatters';

interface AvatarProps {
  name: string;
  size?: 'sm' | 'md' | 'lg';
  online?: boolean;
}

export function Avatar({ name, size = 'md', online = false }: AvatarProps) {
  return (
    <span className={`avatar avatar--${size}`} title={name} aria-label={name}>
      {initials(name)}
      {online ? <span className="avatar__presence" aria-label="Online" /> : null}
    </span>
  );
}
