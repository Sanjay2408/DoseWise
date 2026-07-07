import React from 'react';

// Renders the agent's real action_log entries:
// { type: "REMIND"|"ESCALATE"|"REORDER", what, why, timestamp } or { message, timestamp }
export default function ActionLog({ logs = [] }) {
  const getIcon = (type) => {
    switch ((type || '').toUpperCase()) {
      case 'REMIND': return '⏰';
      case 'ESCALATE': return '📣';
      case 'REORDER': return '🛒';
      default: return 'ℹ️';
    }
  };

  const formatTime = (ts) => {
    if (!ts) return '';
    try {
      return new Date(ts).toLocaleString([], {
        month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit',
      });
    } catch {
      return String(ts);
    }
  };

  const displayLogs = (logs || []).slice(-8).reverse();

  return (
    <div className="action-log card">
      {displayLogs.length === 0 ? (
        <p className="empty-log">Nothing here yet. Activity will show up as you use DoseWise.</p>
      ) : (
        <div className="timeline">
          {displayLogs.map((log, i) => (
            <div key={i} className="timeline-item">
              <div className="timeline-icon" aria-hidden="true">{getIcon(log.type)}</div>
              <div className="timeline-content">
                <h4>{log.what || log.message || log.type || 'Activity'}</h4>
                {log.why && <p>{log.why}</p>}
                <span className="timestamp">{formatTime(log.timestamp)}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      <style jsx>{`
        .empty-log {
            color: var(--text-secondary);
            margin: 0;
        }
        .timeline {
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }
        .timeline-item {
            display: flex;
            gap: 1rem;
            align-items: flex-start;
        }
        .timeline-icon {
            font-size: 1.25rem;
            width: 24px;
            text-align: center;
        }
        .timeline-content h4 {
            margin: 0;
            font-size: 1rem;
            color: var(--text-primary);
        }
        .timeline-content p {
            margin: 0.25rem 0;
            color: var(--text-secondary);
            font-size: 0.875rem;
        }
        .timestamp {
            font-size: 0.75rem;
            color: var(--text-secondary);
            opacity: 0.8;
        }
      `}</style>
    </div>
  );
}
