import React, { useState } from 'react';
import api from '../services/api';

export default function PillCard({ medication, onTake, isUrgent = false }) {
  const [loading, setLoading] = useState(false);
  const [taken, setTaken] = useState(medication.takenToday);

  // Get today's date as key
  const getTodayKey = () => {
    const today = new Date();
    return `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;
  };

  // Get taken doses for today from localStorage
  const getTakenDoses = () => {
    const todayKey = getTodayKey();
    const stored = localStorage.getItem(`doses_${todayKey}`);
    return stored ? JSON.parse(stored) : {};
  };

  // Mark a specific dose time as taken
  const markDoseTaken = (medName, time) => {
    const todayKey = getTodayKey();
    const takenDoses = getTakenDoses();
    if (!takenDoses[medName]) {
      takenDoses[medName] = [];
    }
    if (!takenDoses[medName].includes(time)) {
      takenDoses[medName].push(time);
    }
    localStorage.setItem(`doses_${todayKey}`, JSON.stringify(takenDoses));
  };

  // Check if a specific dose time was taken
  const isDoseTaken = (medName, time) => {
    const takenDoses = getTakenDoses();
    return takenDoses[medName]?.includes(time) || false;
  };

  // Find which dose should be confirmed (current or most recent past dose)
  const getCurrentDose = () => {
    const now = new Date();
    const timings = medication.timings || [medication.time] || ['08:00'];

    let currentDose = null;
    let minDiff = Infinity;

    for (const time of timings) {
      const [hours, minutes] = time.split(':').map(Number);
      const doseTime = new Date(now);
      doseTime.setHours(hours, minutes, 0, 0);

      // Only consider current or past doses
      if (doseTime <= now) {
        const diff = now - doseTime;
        if (diff < minDiff) {
          minDiff = diff;
          currentDose = time;
        }
      }
    }

    return currentDose;
  };

  const handleMarkAsTaken = async () => {
    setLoading(true);
    try {
      const id = medication.id ?? medication.name;
      await api.confirmDose(id);

      // Mark only the current/most recent dose as taken
      const currentDose = getCurrentDose();
      if (currentDose) {
        markDoseTaken(medication.name, currentDose);
      }

      setTaken(true);
      if (onTake) onTake(id);
    } catch (error) {
      console.error('Failed to confirm dose:', error);
      alert("We couldn't record that dose — check your internet and try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={`pill-card ${taken ? 'taken-card' : ''} ${isUrgent ? 'urgent-card' : ''}`}>
      {isUrgent && !taken && (
        <div className="urgent-badge">Overdue — take now</div>
      )}
      <div className="pill-header">
        <div className="pill-title-group">
          <h3>{medication.name}</h3>
          <span className="dosage">{medication.dosage}</span>
        </div>
      </div>

      <div className="pill-content">
        {medication.image && (
          <div className="pill-image-container">
            <img src={medication.image} alt={medication.name} className="pill-image" />
          </div>
        )}

        <div className="pill-details">
          {/* Show all scheduled times with status */}
          {medication.timings && medication.timings.length > 0 ? (
            <div className="detail-item">
              <span className="icon">🕒</span>
              <div className="timings-list">
                {medication.timings.map((time, index) => {
                  const now = new Date();
                  const [hours, minutes] = time.split(':').map(Number);
                  const doseTime = new Date(now);
                  doseTime.setHours(hours, minutes, 0, 0);

                  const isPast = doseTime < now;
                  const twoHoursAgo = new Date(now.getTime() - 2 * 60 * 60 * 1000);
                  const doseTaken = isDoseTaken(medication.name, time);
                  const isUrgentMissed = isPast && doseTime >= twoHoursAgo && !doseTaken;
                  const isMissed = isPast && !doseTaken;
                  const isNext = medication.nextDoseAt && medication.nextDoseAt.includes(time);

                  return (
                    <div key={index} className="timing-item">
                      <span className="timing-time">{time}</span>
                      {doseTaken ? (
                        <span className="timing-badge taken">✓ Taken</span>
                      ) : isUrgentMissed ? (
                        <span className="timing-badge urgent-missed">Take now</span>
                      ) : isMissed ? (
                        <span className="timing-badge missed">Missed earlier</span>
                      ) : isNext ? (
                        <span className="timing-badge next">Coming up next</span>
                      ) : (
                        <span className="timing-badge upcoming">Later today</span>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          ) : (
            <div className="detail-item">
              <span className="icon">🕒</span>
              <span>
                {medication.nextDoseAt ? `Next: ${medication.nextDoseAt}` : medication.time}
              </span>
            </div>
          )}
          <div className="detail-item">
            <span className="icon">📝</span>
            <span>{medication.instructions}</span>
          </div>
        </div>
      </div>

      <div className="pill-actions">
        <button
          onClick={handleMarkAsTaken}
          disabled={taken || loading}
          className={`btn-large btn-take ${taken ? 'btn-success' : 'btn-primary'}`}
        >
          {loading ? 'Saving…' : taken ? '✓ Taken today' : `I took my ${medication.name}`}
        </button>
      </div>

      <style jsx>{`
        .pill-card {
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }
        .pill-title-group {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            flex-wrap: wrap;
        }
        .pill-content {
            display: flex;
            gap: 1rem;
            align-items: start;
        }
        .pill-image-container {
            width: 100px;
            height: 100px;
            border-radius: var(--radius-md);
            overflow: hidden;
            border: 1px solid var(--border-color);
            background: #f8fafc;
            flex-shrink: 0;
        }
        .pill-image {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
        .detail-item {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            margin-bottom: 0.5rem;
            color: var(--text-secondary);
        }
        .btn-success {
            background-color: var(--secondary-color);
            color: white;
        }
        .taken-card {
            border-left-color: var(--secondary-color);
            opacity: 0.8;
        }
        .timings-list {
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
            flex: 1;
        }
        .timing-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 0.75rem;
        }
        .timing-time {
            font-weight: 600;
            color: var(--text-primary);
            min-width: 60px;
        }
        .timing-badge {
            padding: 0.25rem 0.5rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
            white-space: nowrap;
        }
        .timing-badge.taken {
            background: #d1fae5;
            color: #065f46;
        }
        .timing-badge.urgent-missed {
            background: #ef4444;
            color: white;
            animation: pulse-scale 1.5s ease-in-out infinite;
        }
        .timing-badge.missed {
            background: #fecaca;
            color: #991b1b;
        }
        .timing-badge.next {
            background: #dbeafe;
            color: #1e40af;
        }
        .timing-badge.upcoming {
            background: #f3f4f6;
            color: #6b7280;
        }
      `}</style>
    </div>
  );
}
