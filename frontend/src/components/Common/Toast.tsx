import React, { useEffect } from 'react';
import { CheckCircle2 } from 'lucide-react';


interface ToastProps {
  message: string | null;
  onClose: () => void;
  duration?: number;
}

/**
 * Toast Notification component for user action feedbacks.
 */
export const Toast: React.FC<ToastProps> = ({ message, onClose, duration = 3000 }) => {
  useEffect(() => {
    if (!message) return;
    const timer = setTimeout(() => {
      onClose();
    }, duration);
    return () => clearTimeout(timer);
  }, [message, duration, onClose]);

  if (!message) return null;

  return (
    <div className="toast-notification" role="status" aria-live="polite">
      <CheckCircle2 size={18} color="#2ecc71" />
      <span>{message}</span>
    </div>
  );
};
