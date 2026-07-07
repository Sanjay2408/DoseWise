import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import api, { friendlyError } from '../services/api';
import PillCard from '../components/PillCard';
import ReminderModal from '../components/ReminderModal';
import ActionLog from '../components/ActionLog';

// Helper to construct image URL ("<user_id>/<filename>" served from /images)
const getImageUrl = (filename) => {
  if (!filename) return null;
  const baseUrl = process.env.REACT_APP_API_URL ? process.env.REACT_APP_API_URL.replace('/api', '') : 'http://localhost:8000';
  return `${baseUrl}/images/${filename}`;
};

function formatNextDose(iso) {
  if (!iso) return null;
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
  } catch {
    return null;
  }
}

function getNextDueMedication(medications, nowMs, windowMinutes = 30, snoozed = {}) {
  const windowMs = windowMinutes * 60 * 1000;
  for (const m of medications) {
    if (m.takenToday) continue;

    if (snoozed[m.id] && snoozed[m.id] > nowMs) continue;

    const next = m.next_dose_at || m.nextDoseAt;
    if (!next) continue;

    try {
      const nextMs = new Date(next).getTime();
      if (Math.abs(nextMs - nowMs) <= windowMs || (nextMs < nowMs && nowMs - nextMs < 12 * 60 * 60 * 1000)) return m;
    } catch (e) { }
  }
  return null;
}

export default function Dashboard() {
  const [medications, setMedications] = useState([]);
  const [profile, setProfile] = useState({ name: '', age: '', conditions: '' });
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [activeReminder, setActiveReminder] = useState(null);
  const [snoozed, setSnoozed] = useState({}); // Map of id -> timestamp (snoozed until)
  const [takenConfirmation, setTakenConfirmation] = useState(null); // medication name just confirmed
  const [actionLog, setActionLog] = useState([]);

  const loadData = useCallback(async () => {
    try {
      const state = await api.getCurrentState();
      const meds = state.medications || [];
      setProfile(state.patient_profile || { name: '', age: '', conditions: '' });
      setMedications(
        meds.map((m, i) => ({
          id: m.name || i,
          name: m.name,
          dosage: m.dosage || '',
          timings: m.timings || ['08:00'],
          time: (m.timings && m.timings[0]) ? m.timings[0] : '08:00',
          instructions:
            (m.before_after_food === 'anytime' ? 'Take as directed' : `Take ${m.before_after_food} food`),
          takenToday: !!m.last_taken_at,
          image: getImageUrl(m.image_file),
          next_dose_at: m.next_dose_at,
          nextDoseAt: m.next_dose_at ? formatNextDose(m.next_dose_at) : null,
        }))
      );
      setActionLog(state.action_log || []);
      setLoadError('');
    } catch (e) {
      console.error(e);
      setMedications([]);
      setLoadError(friendlyError(e, "We couldn't load your medications. Please try again in a moment."));
    } finally {
      setLoading(false);
    }
  }, []);

  // Use ref to track active reminder to avoid dependency loops in effect
  const activeReminderRef = React.useRef(activeReminder);

  useEffect(() => {
    activeReminderRef.current = activeReminder;
  }, [activeReminder]);

  useEffect(() => {
    if (loading) return;

    const check = () => {
      if (activeReminderRef.current) return;

      const due = getNextDueMedication(medications, Date.now(), 30, snoozed);
      if (due) {
        const formattedId = due.id || due.name;
        setActiveReminder({
          id: formattedId,
          medicationName: due.name,
          dosage: due.dosage || '',
          instructions: due.instructions,
        });
      }
    };

    check();
    const interval = setInterval(check, 30000); // Check every 30s
    return () => clearInterval(interval);
  }, [medications, snoozed, loading]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleTakeMedication = async (idOrName) => {
    const medName = typeof idOrName === 'string' ? idOrName : (medications.find((m) => m.id === idOrName)?.name || 'Medication');
    try {
      const payload = typeof idOrName === 'number'
        ? { medication_id: idOrName }
        : { medication_name: idOrName };

      await api.confirmDose(payload);
      await loadData();

      // Unmistakable full-screen confirmation so there's no doubt the tap registered
      setTakenConfirmation(medName);
      setTimeout(() => setTakenConfirmation(null), 3500);

      if (activeReminder) {
        const matchesId = activeReminder.id === idOrName;
        const matchesName = activeReminder.medicationName === idOrName;
        if (matchesId || matchesName) {
          setActiveReminder(null);
        }
      }
    } catch (err) {
      console.error('Error confirming dose:', err);
      setLoadError(friendlyError(err, "We couldn't record that dose — check your internet and try again."));
      if (activeReminder) {
        const matchesId = activeReminder.id === idOrName;
        const matchesName = activeReminder.medicationName === idOrName;
        if (matchesId || matchesName) {
          setActiveReminder(null);
        }
      }
    }
  };

  const handleCloseReminder = () => {
    setActiveReminder(null);
  };

  const handleSnooze = (id) => {
    const snoozeUntil = Date.now() + 10 * 60 * 1000; // 10 minutes
    setSnoozed(prev => ({ ...prev, [id]: snoozeUntil }));
    setActiveReminder(null);
  };

  if (loading) return <div className="text-center mt-4">Loading…</div>;

  const patientName = profile.name || 'there';
  const pendingCount = medications.filter((m) => !m.takenToday).length;

  // Check for urgent missed doses (within past 2 hours)
  const now = new Date();
  const twoHoursAgo = new Date(now.getTime() - 2 * 60 * 60 * 1000);

  const urgentMissedDoses = medications.filter(med => {
    if (med.takenToday) return false;

    const timings = med.timings || [med.time] || ['08:00'];
    return timings.some(time => {
      const [hours, minutes] = time.split(':').map(Number);
      const doseTime = new Date(now);
      doseTime.setHours(hours, minutes, 0, 0);

      // Only flag if dose time is in the PAST and within last 2 hours
      return doseTime < now && doseTime >= twoHoursAgo;
    });
  });

  // Sort medications: urgent missed first, then pending, then taken
  const sortedMedications = [...medications].sort((a, b) => {
    const aUrgent = urgentMissedDoses.includes(a);
    const bUrgent = urgentMissedDoses.includes(b);

    if (aUrgent && !bUrgent) return -1;
    if (!aUrgent && bUrgent) return 1;

    if (!a.takenToday && b.takenToday) return -1;
    if (a.takenToday && !b.takenToday) return 1;

    return 0;
  });

  return (
    <div className="dashboard">
      {takenConfirmation && (
        <div className="fullscreen-confirm overlay" role="status" aria-live="assertive">
          <div className="confirm-check">✓</div>
          <h1>{takenConfirmation} marked as taken</h1>
          <p>Well done!</p>
        </div>
      )}

      <section className="welcome-section">
        <h1>Hello, {patientName}! 👋</h1>
        <p className="welcome-status">
          {medications.length === 0
            ? 'Let’s add your medications to get started.'
            : pendingCount > 0
              ? `You have ${pendingCount} medication${pendingCount > 1 ? 's' : ''} left to take today.`
              : 'All medications taken for today. Great job! 🎉'}
        </p>
        {urgentMissedDoses.length > 0 && (
          <div className="urgent-alert" role="alert">
            <div className="urgent-alert-icon" aria-hidden="true">⚠️</div>
            <div className="urgent-alert-content">
              <strong>Overdue — please take now</strong>
              <p>
                {urgentMissedDoses.map((m) => m.name).join(', ')} {urgentMissedDoses.length > 1 ? 'were' : 'was'} due earlier today.
              </p>
            </div>
          </div>
        )}
        {loadError && (
          <div className="load-error" role="alert">{loadError}</div>
        )}
      </section>

      <section className="medications-section">
        <div className="section-header">
          <h2>Today's medicines</h2>
          {medications.length > 0 && <span className="badge">{pendingCount} to take</span>}
        </div>
        {medications.length === 0 ? (
          <div className="empty-state">
            <p>No medications yet.</p>
            <Link to="/setup" className="btn-primary btn-large empty-cta">Add my medications</Link>
          </div>
        ) : (
          <div className="medications-list">
            {sortedMedications.map((med) => {
              const isUrgent = urgentMissedDoses.includes(med);
              return (
                <PillCard
                  key={med.id}
                  medication={med}
                  onTake={handleTakeMedication}
                  isUrgent={isUrgent}
                />
              );
            })}
          </div>
        )}
      </section>

      <section className="quick-actions">
        <Link to="/wellbeing" className="quick-action-btn">
          <span aria-hidden="true">💬</span> Tell us how you feel today
        </Link>
      </section>

      <section className="action-log-section">
        <h2>Recent activity</h2>
        <ActionLog logs={actionLog} />
      </section>

      <ReminderModal
        reminder={activeReminder}
        onClose={handleCloseReminder}
        onSnooze={handleSnooze}
        onConfirm={(id) => handleTakeMedication(id || activeReminder?.id)}
      />

      <style jsx>{`
        .dashboard {
          max-width: 720px;
          margin: 0 auto;
        }
        .welcome-status {
          font-size: 1.15rem;
          color: var(--text-secondary);
        }
        .section-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin: 1.5rem 0 1rem;
        }
        .badge {
          background: #eff6ff;
          color: var(--primary-color);
          padding: 0.35rem 1rem;
          border-radius: 9999px;
          font-weight: 700;
          font-size: 1rem;
        }
        .empty-state {
          color: var(--text-secondary);
          padding: 2rem;
          text-align: center;
        }
        .empty-cta {
          display: inline-block;
          margin-top: 1rem;
          text-decoration: none;
          text-align: center;
        }
        .quick-actions {
          margin: 2rem 0;
        }
        .quick-action-btn {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 0.75rem;
          width: 100%;
          padding: 1.25rem;
          font-size: 1.25rem;
          font-weight: 700;
          color: var(--primary-color);
          background: var(--surface-color);
          border: 2px solid var(--primary-color);
          border-radius: var(--radius-lg);
          text-decoration: none;
        }
        .quick-action-btn:hover {
          background: #eff6ff;
        }
        .load-error {
          margin-top: 1rem;
          padding: 1rem;
          border-radius: var(--radius-md);
          background: #fef2f2;
          border: 1px solid #fecaca;
          color: #991b1b;
        }
        .action-log-section {
          margin-top: 2rem;
        }
      `}</style>
    </div>
  );
}
