import { IconCheckCircle, IconInfo, IconWarning, IconError, IconClose } from '../icons';
import type { ToastMessage } from '../../types';

interface ToastStackProps {
  toasts: ToastMessage[];
  onDismiss: (id: string) => void;
}

const icons = {
  success: IconCheckCircle,
  info: IconInfo,
  warning: IconWarning,
  danger: IconError,
};

export function ToastStack({ toasts, onDismiss }: ToastStackProps) {
  return (
    <div className="toast-stack" aria-live="polite" aria-atomic="false">
      {toasts.map((toast) => {
        const Icon = icons[toast.tone];
        return (
          <article key={toast.id} className={`toast toast--${toast.tone}`}>
            <span className="toast__icon">
              <Icon size={19} />
            </span>
            <div className="toast__copy">
              <strong>{toast.title}</strong>
              {toast.message ? <p>{toast.message}</p> : null}
            </div>
            <button onClick={() => onDismiss(toast.id)} aria-label="Dismiss notification">
              <IconClose size={16} />
            </button>
          </article>
        );
      })}
    </div>
  );
}
