import React from 'react';

export default function MedicationTimeline({ medications = [] }) {
  // Group medications by time and status
  const now = new Date();
  const currentHour = now.getHours();
  const currentMinute = now.getMinutes();

  // Helper to get taken doses from localStorage (same usage as PillCard)
  const getTodayKey = () => {
    const today = new Date();
    return `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;
  };

  const getTakenDoses = () => {
    const todayKey = getTodayKey();
    const stored = localStorage.getItem(`doses_${todayKey}`);
    return stored ? JSON.parse(stored) : {};
  };

  const takenDosesMap = getTakenDoses();

  const isDoseTaken = (medName, time) => {
    return takenDosesMap[medName]?.includes(time) || false;
  };

  // Expand medications to individual doses based on timings
  const allDoses = [];
  medications.forEach(med => {
    const timings = med.timings || [med.time] || ['08:00'];
    timings.forEach(time => {
      const [hours, minutes] = time.split(':').map(Number);
      const timeInMinutes = hours * 60 + minutes;
      const currentTimeInMinutes = currentHour * 60 + currentMinute;

      const doseTaken = isDoseTaken(med.name, time);

      allDoses.push({
        medicationName: med.name,
        dosage: med.dosage,
        time: time,
        timeInMinutes: timeInMinutes,
        taken: doseTaken, // Use specific dose status
        isPast: timeInMinutes < currentTimeInMinutes,
        isCurrent: Math.abs(timeInMinutes - currentTimeInMinutes) <= 30, // Within 30 min window
      });
    });
  });

  // Sort by time
  allDoses.sort((a, b) => a.timeInMinutes - b.timeInMinutes);

  const takenCount = allDoses.filter(d => d.taken).length;
  const pendingCount = allDoses.filter(d => !d.taken).length;

  return (
    <div className="medication-timeline">
      <div className="timeline-header">
        <h3>📅 Today's Medication Schedule</h3>
        <div className="timeline-stats">
          <span className="stat-taken">✓ {takenCount} Taken</span>
          <span className="stat-pending">⏳ {pendingCount} Pending</span>
        </div>
      </div>

      <div className="timeline-container">
        {allDoses.length === 0 ? (
          <p className="empty-timeline">No medications scheduled for today</p>
        ) : (
          <div className="timeline-items">
            {allDoses.map((dose, index) => (
              <div
                key={`${dose.medicationName}-${dose.time}-${index}`}
                className={`timeline-item ${dose.taken ? 'taken' : dose.isPast ? 'missed' : dose.isCurrent ? 'current' : 'upcoming'}`}
              >
                <div className="timeline-marker">
                  <div className="timeline-dot"></div>
                  {index < allDoses.length - 1 && <div className="timeline-line"></div>}
                </div>
                <div className="timeline-content">
                  <div className="timeline-time">{dose.time}</div>
                  <div className="timeline-med-info">
                    <strong>{dose.medicationName}</strong>
                    <span className="timeline-dosage">{dose.dosage}</span>
                  </div>
                  <div className="timeline-status">
                    {dose.taken ? (
                      <span className="status-badge taken">✓ Taken</span>
                    ) : dose.isPast ? (
                      <span className="status-badge missed">⚠️ Missed</span>
                    ) : dose.isCurrent ? (
                      <span className="status-badge current">⏰ Due Now</span>
                    ) : (
                      <span className="status-badge upcoming">⏳ Upcoming</span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <style jsx>{`
        .medication-timeline {
          background: white;
          border-radius: 12px;
          padding: 1.5rem;
          box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .timeline-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 1.5rem;
          padding-bottom: 1rem;
          border-bottom: 2px solid #e5e7eb;
        }
        .timeline-header h3 {
          margin: 0;
          font-size: 1.25rem;
          color: #1f2937;
        }
        .timeline-stats {
          display: flex;
          gap: 1rem;
        }
        .stat-taken {
          color: #10b981;
          font-weight: 600;
        }
        .stat-pending {
          color: #f59e0b;
          font-weight: 600;
        }
        .timeline-container {
          position: relative;
        }
        .timeline-items {
          display: flex;
          flex-direction: column;
          gap: 0;
        }
        .timeline-item {
          display: flex;
          gap: 1rem;
          position: relative;
          padding: 0.75rem 0;
        }
        .timeline-marker {
          display: flex;
          flex-direction: column;
          align-items: center;
          position: relative;
        }
        .timeline-dot {
          width: 16px;
          height: 16px;
          border-radius: 50%;
          border: 3px solid #e5e7eb;
          background: white;
          z-index: 1;
        }
        .timeline-item.taken .timeline-dot {
          background: #10b981;
          border-color: #10b981;
        }
        .timeline-item.current .timeline-dot {
          background: #3b82f6;
          border-color: #3b82f6;
          box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.2);
        }
        .timeline-item.missed .timeline-dot {
          background: #ef4444;
          border-color: #ef4444;
        }
        .timeline-item.upcoming .timeline-dot {
          background: white;
          border-color: #9ca3af;
        }
        .timeline-line {
          width: 2px;
          flex: 1;
          background: #e5e7eb;
          margin-top: 4px;
        }
        .timeline-item.taken .timeline-line {
          background: #10b981;
        }
        .timeline-content {
          flex: 1;
          display: flex;
          align-items: center;
          gap: 1rem;
          padding: 0.5rem 1rem;
          border-radius: 8px;
          background: #f9fafb;
        }
        .timeline-item.taken .timeline-content {
          background: #d1fae5;
        }
        .timeline-item.current .timeline-content {
          background: #dbeafe;
          border: 2px solid #3b82f6;
        }
        .timeline-item.missed .timeline-content {
          background: #fee2e2;
        }
        .timeline-time {
          font-weight: 700;
          color: #374151;
          min-width: 60px;
          font-size: 1rem;
        }
        .timeline-med-info {
          flex: 1;
          display: flex;
          flex-direction: column;
        }
        .timeline-med-info strong {
          color: #1f2937;
          font-size: 1rem;
        }
        .timeline-dosage {
          color: #6b7280;
          font-size: 0.875rem;
        }
        .timeline-status {
          margin-left: auto;
        }
        .status-badge {
          padding: 0.25rem 0.75rem;
          border-radius: 9999px;
          font-size: 0.875rem;
          font-weight: 600;
        }
        .status-badge.taken {
          background: #10b981;
          color: white;
        }
        .status-badge.current {
          background: #3b82f6;
          color: white;
        }
        .status-badge.missed {
          background: #ef4444;
          color: white;
        }
        .status-badge.upcoming {
          background: #9ca3af;
          color: white;
        }
        .empty-timeline {
          text-align: center;
          color: #9ca3af;
          padding: 2rem;
        }
      `}</style>
    </div>
  );
}
