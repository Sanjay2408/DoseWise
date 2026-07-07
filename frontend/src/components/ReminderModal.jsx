import React from 'react';

export default function ReminderModal({ reminder, onClose, onSnooze, onConfirm }) {
  if (!reminder) return null;

  return (
    <div className="modal-overlay">
      <div className="modal-content">
        <div className="modal-header">
          <h2>⏰ Medication Reminder</h2>
        </div>

        <div className="modal-body">
          <p className="reminder-text">It's time to take your medication:</p>
          <div className="reminder-med">
            <h3>{reminder.medicationName}</h3>
            <span className="reminder-dosage">{reminder.dosage}</span>
          </div>
          <p className="reminder-instructions">{reminder.instructions}</p>
        </div>

        <div className="modal-actions">
          <button onClick={() => onConfirm(reminder.id)} className="btn-primary btn-large">
            Take Now
          </button>
          <button onClick={() => onSnooze(reminder.id)} className="btn-secondary">
            Snooze 10m
          </button>
          <button onClick={onClose} className="btn-text">
            Dismiss
          </button>
        </div>
      </div>

      <style jsx>{`
        .modal-overlay {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: rgba(0, 0, 0, 0.7);
          display: flex;
          justify-content: center;
          align-items: center;
          z-index: 1000;
          backdrop-filter: blur(4px);
        }
        .modal-content {
          background: white;
          padding: 2rem;
          border-radius: var(--radius-lg);
          width: 90%;
          max-width: 400px;
          box-shadow: var(--shadow-lg);
          animation: slideIn 0.3s ease-out;
        }
        .modal-header h2 {
           color: var(--primary-color);
           margin-top: 0;
        }
        .reminder-med {
            background: #eff6ff;
            padding: 1rem;
            border-radius: var(--radius-md);
            margin: 1rem 0;
            text-align: center;
        }
        .reminder-med h3 { margin: 0; margin-bottom: 0.25rem; }
        .modal-actions {
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
            margin-top: 1.5rem;
        }
        .btn-secondary {
            background: white;
            border: 1px solid var(--border-color);
            color: var(--text-secondary);
            padding: 0.75rem;
            border-radius: var(--radius-md);
        }
        .btn-text {
            background: transparent;
            color: var(--text-secondary);
            text-decoration: underline;
            padding: 0.5rem;
        }
        @keyframes slideIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
}
