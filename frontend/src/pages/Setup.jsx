import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api, { friendlyError } from '../services/api';



export default function Setup() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [hasExistingProfile, setHasExistingProfile] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    age: '',
    conditions: '',

    medications: [{ name: '', dosage: '', quantity: 30, times: ['08:00'], take_with_food: 'after', file: null }],
  });

  useEffect(() => {
    const load = async () => {
      try {
        const state = await api.getCurrentState();
        const profile = state.patient_profile || {};
        const meds = state.medications || [];
        const inventory = state.inventory || [];
        if (profile.name || (meds && meds.length > 0)) {
          setHasExistingProfile(true);
          setFormData({
            name: profile.name || '',
            age: profile.age || '',
            conditions: profile.conditions || '',
            medications: meds.length > 0
              ? meds.map((m) => {
                const invItem = inventory.find(i => (i.med_name || i.name || i.id) === (m.name || m.id));
                return {
                  name: m.name || '',
                  dosage: m.dosage || '',
                  quantity: invItem ? invItem.quantity : 30,
                  times: Array.isArray(m.timings) ? [...m.timings] : [m.timings || '08:00'].filter(Boolean),
                  take_with_food: m.before_after_food || 'anytime',
                  file: null,
                };
              })
              : [{ name: '', dosage: '', quantity: 30, times: ['08:00'], take_with_food: 'after', file: null }],
          });
        }
      } catch (e) {
        console.error(e);
      }
    };
    load();
  }, []);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData({ ...formData, [name]: value });
  };

  const handleMedChange = (index, field, value) => {
    const newMeds = [...formData.medications];
    newMeds[index] = { ...newMeds[index], [field]: value };
    setFormData({ ...formData, medications: newMeds });
  };

  const handleFileChange = (index, e) => {
    if (e.target.files && e.target.files[0]) {
      handleMedChange(index, 'file', e.target.files[0]);
    }
  };

  const handleTimeChange = (medIndex, timeIndex, value) => {
    const newMeds = [...formData.medications];
    const times = [...(newMeds[medIndex].times || ['08:00'])];
    times[timeIndex] = value;
    newMeds[medIndex] = { ...newMeds[medIndex], times };
    setFormData({ ...formData, medications: newMeds });
  };

  const addTimeSlot = (medIndex) => {
    const newMeds = [...formData.medications];
    const times = [...(newMeds[medIndex].times || ['08:00']), '12:00'];
    newMeds[medIndex] = { ...newMeds[medIndex], times };
    setFormData({ ...formData, medications: newMeds });
  };

  const removeTimeSlot = (medIndex, timeIndex) => {
    const newMeds = [...formData.medications];
    const times = (newMeds[medIndex].times || ['08:00']).filter((_, i) => i !== timeIndex);
    if (times.length === 0) times.push('08:00');
    newMeds[medIndex] = { ...newMeds[medIndex], times };
    setFormData({ ...formData, medications: newMeds });
  };

  const addMedication = () => {
    setFormData({
      ...formData,
      medications: [...formData.medications, { name: '', dosage: '', quantity: 30, times: ['08:00'], take_with_food: 'after', file: null }],
    });
  };

  const handleRemoveMedication = async (index) => {
    const medToRemove = formData.medications[index];
    if (hasExistingProfile && medToRemove.name) {
      if (window.confirm(`Are you sure you want to delete ${medToRemove.name}? This cannot be undone.`)) {
        try {
          await api.deleteMedication(medToRemove.name);
        } catch (error) {
          console.error('Failed to delete medication from backend', error);
          alert('Could not delete from backend, but removing from list.');
        }
      } else {
        return;
      }
    }
    setFormData((prev) => ({
      ...prev,
      medications: prev.medications.filter((_, i) => i !== index),
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const payload = {
        name: formData.name || undefined,
        age: formData.age || undefined,
        conditions: formData.conditions || undefined,
        medications: formData.medications
          .filter((m) => (m.name || '').trim())
          .map((m) => ({
            name: m.name.trim(),
            dosage: m.dosage || '',
            quantity: parseInt(m.quantity || 30, 10),
            times: (m.times && m.times.length) ? m.times : ['08:00'],
            take_with_food: m.take_with_food || 'anytime',
          })),
      };
      await api.submitSetup(payload);

      // Upload images sequentially
      for (const med of formData.medications) {
        if (med.name && med.file) {
          try {
            await api.uploadMedicationImage(med.name.trim(), med.file);
          } catch (err) {
            console.error(`Failed to upload image for ${med.name}`, err);
          }
        }
      }

      navigate('/');
    } catch (err) {
      console.error('Setup failed:', err);
      setError(friendlyError(err, "We couldn't save your details — check your internet and try again."));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="setup-page">
      <h1>{hasExistingProfile ? 'Edit profile & add medications' : "Let's Get Started"}</h1>
      {hasExistingProfile && (
        <p className="setup-hint">Update patient details and add more medications or inventory as needed.</p>
      )}

      {error && <div className="auth-error" role="alert">{error}</div>}

      <form onSubmit={handleSubmit} className="setup-form">
        <div className="form-section">
          <h2>Patient Details</h2>
          <div className="form-group">
            <label htmlFor="name">Full Name</label>
            <input
              type="text"
              id="name"
              name="name"
              value={formData.name}
              onChange={handleInputChange}
              required
              placeholder="e.g. John Doe"
            />
          </div>
          <div className="form-group">
            <label htmlFor="age">Age</label>
            <input
              type="number"
              id="age"
              name="age"
              value={formData.age}
              onChange={handleInputChange}
              required
              placeholder="e.g. 65"
            />
          </div>
          <div className="form-group">
            <label htmlFor="conditions">Medical Conditions</label>
            <textarea
              id="conditions"
              name="conditions"
              value={formData.conditions}
              onChange={handleInputChange}
              placeholder="e.g. Hypertension, Diabetes Type 2"
              rows={3}
            />
          </div>
        </div>

        <div className="form-section">
          <h2>Medications</h2>
          <p className="form-hint">Add times to take (e.g. 8am, 8pm) and whether before/after food.</p>
          {formData.medications.map((med, index) => (
            <div key={index} className="medication-entry">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                <h4 style={{ margin: 0 }}>Medication {index + 1}</h4>
                {formData.medications.length > 0 && (
                  <button
                    type="button"
                    onClick={() => handleRemoveMedication(index)}
                    style={{ color: '#ef4444', background: 'none', border: 'none', cursor: 'pointer', fontWeight: 600 }}
                  >
                    Delete
                  </button>
                )}
              </div>
              <div className="grid-2">
                <input
                  type="text"
                  placeholder="Medication Name"
                  value={med.name}
                  onChange={(e) => handleMedChange(index, 'name', e.target.value)}
                  required
                />
                <input
                  type="text"
                  placeholder="Dosage (e.g. 10mg)"
                  value={med.dosage}
                  onChange={(e) => handleMedChange(index, 'dosage', e.target.value)}
                  required
                />
              </div>
              <div className="grid-2 mt-2">
                <div>
                  <label>Quantity (Stock)</label>
                  <input
                    type="number"
                    placeholder="30"
                    value={med.quantity}
                    onChange={(e) => handleMedChange(index, 'quantity', e.target.value)}
                    min="0"
                    style={{ width: '100%' }}
                  />
                </div>
                <div>
                  <label>Image (Optional)</label>
                  <input
                    type="file"
                    accept="image/*"
                    onChange={(e) => handleFileChange(index, e)}
                    style={{ width: '100%' }}
                  />
                </div>
              </div>
              <div className="times-row">
                <label>Times to take</label>
                {(med.times || ['08:00']).map((t, ti) => (
                  <div key={ti} className="time-slot">
                    <input
                      type="time"
                      value={t}
                      onChange={(e) => handleTimeChange(index, ti, e.target.value)}
                    />
                    {(med.times || []).length > 1 && (
                      <button type="button" className="btn-remove-time" onClick={() => removeTimeSlot(index, ti)}>
                        ×
                      </button>
                    )}
                  </div>
                ))}
                <button type="button" className="btn-add-time" onClick={() => addTimeSlot(index)}>
                  + Add time
                </button>
              </div>
              <div className="take-with-food">
                <label>Take with food</label>
                <select
                  value={med.take_with_food || 'anytime'}
                  onChange={(e) => handleMedChange(index, 'take_with_food', e.target.value)}
                >
                  <option value="before">Before food</option>
                  <option value="after">After food</option>
                  <option value="anytime">Anytime</option>
                </select>
              </div>
            </div>
          ))}
          <button type="button" onClick={addMedication} className="btn-secondary mt-2 w-full">
            + Add Another Medication
          </button>
        </div>

        <div className="form-actions mt-4">
          <button type="submit" className="btn-primary btn-large" disabled={loading}>
            {loading ? (hasExistingProfile ? 'Saving...' : 'Setting up...') : hasExistingProfile ? 'Save changes' : 'Complete Setup'}
          </button>
        </div>
      </form>

      <style jsx>{`
        .form-section {
          margin-bottom: 2rem;
          border-bottom: 1px solid var(--border-color);
          padding-bottom: 2rem;
        }
        .form-section:last-of-type {
          border-bottom: none;
        }
        .setup-hint,
        .form-hint {
          color: var(--text-secondary);
          font-size: 0.9rem;
          margin-bottom: 1rem;
        }
        .medication-entry {
          background: #f8fafc;
          padding: 1rem;
          border-radius: var(--radius-md);
          border: 1px solid var(--border-color);
          margin-bottom: 1rem;
        }
        .grid-2 {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 1rem;
        }
        .times-row label,
        .take-with-food label {
          display: block;
          margin-bottom: 0.25rem;
          font-size: 0.875rem;
        }
        .time-slot {
          display: inline-flex;
          align-items: center;
          gap: 0.25rem;
          margin-right: 0.5rem;
          margin-bottom: 0.5rem;
        }
        .time-slot input {
          padding: 0.5rem;
          border-radius: var(--radius-md);
          border: 1px solid var(--border-color);
        }
        .btn-remove-time,
        .btn-add-time {
          padding: 0.25rem 0.5rem;
          font-size: 0.875rem;
          border-radius: var(--radius-md);
          border: 1px solid var(--border-color);
          background: white;
          cursor: pointer;
        }
        .btn-add-time {
          color: var(--primary-color);
        }
        .take-with-food select {
          width: 100%;
          max-width: 200px;
          padding: 0.5rem;
          border-radius: var(--radius-md);
          border: 1px solid var(--border-color);
        }
        .mt-2 {
          margin-top: 0.5rem;
        }
        .w-full {
          width: 100%;
        }
        .btn-secondary {
          background: white;
          border: 1px dashed var(--border-color);
          color: var(--primary-color);
          padding: 0.75rem;
          border-radius: var(--radius-md);
          width: 100%;
        }
        .btn-secondary:hover {
          border-color: var(--primary-color);
          background: #eff6ff;
        }
      `}</style>
    </div>
  );
}
