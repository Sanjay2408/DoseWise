import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api, { friendlyError } from '../services/api';

const FEELINGS = [
  { value: 'well', label: 'Feeling well', emoji: '😊' },
  { value: 'ok', label: 'Okay', emoji: '🙂' },
  { value: 'tired', label: 'Tired', emoji: '😴' },
  { value: 'unwell', label: 'Not well', emoji: '😟' },
];

export default function Wellbeing() {
  const navigate = useNavigate();
  const [feeling, setFeeling] = useState('');
  const [vitals, setVitals] = useState({ blood_pressure: '', heart_rate: '', temperature: '' });
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!feeling && !vitals.blood_pressure && !vitals.heart_rate && !vitals.temperature) {
      setError('Please choose how you feel, or enter at least one reading.');
      return;
    }
    setError('');
    setSaving(true);
    try {
      await api.submitVitals({
        feeling: feeling || undefined,
        blood_pressure: vitals.blood_pressure || undefined,
        heart_rate: vitals.heart_rate ? parseInt(vitals.heart_rate, 10) : undefined,
        temperature: vitals.temperature ? parseFloat(vitals.temperature) : undefined,
      });
      setSaved(true);
    } catch (err) {
      setError(friendlyError(err, "We couldn't save that — check your internet and try again."));
    } finally {
      setSaving(false);
    }
  };

  if (saved) {
    return (
      <div className="fullscreen-confirm" role="status">
        <div className="confirm-check">✓</div>
        <h1>Saved — thank you!</h1>
        <p>Your update has been recorded.</p>
        <button className="btn-primary btn-large" onClick={() => navigate('/')}>
          Back to Home
        </button>
      </div>
    );
  }

  return (
    <div className="wellbeing-page">
      <h1>How are you feeling today?</h1>
      <p className="page-hint">Tap the one that fits best.</p>

      {error && <div className="auth-error" role="alert">{error}</div>}

      <form onSubmit={handleSubmit}>
        <div className="feeling-buttons">
          {FEELINGS.map((f) => (
            <button
              key={f.value}
              type="button"
              className={`feeling-btn ${feeling === f.value ? 'selected' : ''}`}
              onClick={() => setFeeling(f.value)}
              aria-pressed={feeling === f.value}
            >
              <span className="feeling-emoji" aria-hidden="true">{f.emoji}</span>
              <span>{f.label}</span>
            </button>
          ))}
        </div>

        <div className="card vitals-card">
          <h2>Health readings (optional)</h2>
          <p className="page-hint">Only fill in what you measured today.</p>
          <div className="form-group">
            <label htmlFor="bp">Blood pressure (for example 120/80)</label>
            <input
              id="bp"
              type="text"
              inputMode="numeric"
              placeholder="120/80"
              value={vitals.blood_pressure}
              onChange={(e) => setVitals((v) => ({ ...v, blood_pressure: e.target.value }))}
            />
          </div>
          <div className="form-group">
            <label htmlFor="hr">Heart rate (beats per minute)</label>
            <input
              id="hr"
              type="number"
              placeholder="72"
              value={vitals.heart_rate}
              onChange={(e) => setVitals((v) => ({ ...v, heart_rate: e.target.value }))}
            />
          </div>
          <div className="form-group">
            <label htmlFor="temp">Temperature (°C)</label>
            <input
              id="temp"
              type="number"
              step="0.1"
              placeholder="36.8"
              value={vitals.temperature}
              onChange={(e) => setVitals((v) => ({ ...v, temperature: e.target.value }))}
            />
          </div>
        </div>

        <button type="submit" className="btn-primary btn-large" disabled={saving}>
          {saving ? 'Saving…' : 'Save my update'}
        </button>
      </form>

      <style jsx>{`
        .wellbeing-page {
          max-width: 560px;
          margin: 0 auto;
        }
        .feeling-buttons {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 1rem;
          margin: 1.5rem 0;
        }
        .feeling-btn {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 0.5rem;
          padding: 1.5rem 1rem;
          font-size: 1.15rem;
          border: 2px solid var(--border-color);
          border-radius: var(--radius-lg);
          background: var(--surface-color);
        }
        .feeling-btn.selected {
          border-color: var(--primary-color);
          background: #eff6ff;
          font-weight: 700;
        }
        .feeling-emoji {
          font-size: 2.5rem;
        }
        .vitals-card {
          margin-bottom: 1.5rem;
        }
      `}</style>
    </div>
  );
}
