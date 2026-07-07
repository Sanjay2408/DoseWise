import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import api from '../services/api';
import InventoryStatus from '../components/InventoryStatus';
import MedicationTimeline from '../components/MedicationTimeline';

export default function Caregiver() {
  const [dashboard, setDashboard] = useState(null);
  const [dailyReports, setDailyReports] = useState(null);
  const [selectedDate, setSelectedDate] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [alerts, setAlerts] = useState([]);

  const profile = dashboard?.profile || {};
  const medications = dashboard?.medications || [];
  const trendAlerts = dashboard?.trend_alerts || [];
  const aiSummary = dashboard?.ai_summary || '';
  const severity = dashboard?.severity || 'low';
  const trends = dashboard?.trends || {};
  // Removed unused 'vitals' variable
  const byType = trends.by_type || {};
  const dates = dailyReports?.dates || [];
  const reports = dailyReports?.reports || {};
  const selectedReport = selectedDate ? reports[selectedDate] : null;

  useEffect(() => {
    const load = async () => {
      try {
        const [data, reportsData] = await Promise.all([
          api.getCaregiverDashboard(),
          api.getDailyReports().catch(() => ({ dates: [], reports: {} })),
        ]);
        setDashboard(data);
        setDailyReports(reportsData);
        const combined = (data.alerts || []).map((a, i) => ({
          id: i + 1,
          title: String(a).startsWith('[Trend]') ? 'Trend Alert' : 'Alert',
          message: String(a).replace(/^\[Trend\]\s*/, ''),
          timestamp: '',
          severity: data.severity === 'high' || data.severity === 'critical' ? 'high' : 'medium',
        }));
        setAlerts(
          combined.length > 0
            ? combined
            : [{ id: 1, title: 'No alerts', message: 'No active alerts. Patient data within expected ranges.', timestamp: '', severity: 'low' }]
        );
        if (reportsData.dates && reportsData.dates.length > 0 && !selectedDate) {
          setSelectedDate(reportsData.dates[0]);
        }
      } catch (e) {
        console.error(e);
        setAlerts([{ id: 1, title: 'No data', message: 'Could not load dashboard. Ensure backend is running.', timestamp: '', severity: 'low' }]);
      } finally {
        setLoading(false);
      }
    };
    load();

    // Poll periodically to keep data fresh (e.g. taken status)
    const interval = setInterval(load, 30000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleRefreshTrends = async () => {
    setRefreshing(true);
    try {
      await api.runAgent();
      const [data, reportsData] = await Promise.all([
        api.getCaregiverDashboard(),
        api.getDailyReports().catch(() => ({ dates: [], reports: {} })),
      ]);
      setDashboard(data);
      setDailyReports(reportsData);
      const combined = (data.alerts || []).map((a, i) => ({
        id: i + 1,
        title: String(a).startsWith('[Trend]') ? 'Trend Alert' : 'Alert',
        message: String(a).replace(/^\[Trend\]\s*/, ''),
        timestamp: '',
        severity: data.severity === 'high' || data.severity === 'critical' ? 'high' : 'medium',
      }));
      setAlerts(combined.length > 0 ? combined : [{ id: 1, title: 'No alerts', message: 'No active alerts.', timestamp: '', severity: 'low' }]);
    } catch (e) {
      console.error(e);
    } finally {
      setRefreshing(false);
    }
  };



  if (loading) {
    return (
      <div className="caregiver-page">
        <p className="text-center">Loading caregiver dashboard...</p>
      </div>
    );
  }

  const latestBp =
    byType.blood_pressure?.length ? byType.blood_pressure[byType.blood_pressure.length - 1]?.value : null;
  const latestSugar = byType.blood_sugar?.length ? byType.blood_sugar[byType.blood_sugar.length - 1]?.value : null;

  return (
    <div className="caregiver-page">
      <div className="caregiver-header">
        <h1>Caregiver Dashboard</h1>
        <button type="button" className="btn-primary" onClick={handleRefreshTrends} disabled={refreshing}>
          {refreshing ? 'Refreshing...' : 'Refresh trends'}
        </button>
      </div>

      <div className="caregiver-grid">
        {/* What-to-look-at first: alerts and AI summary above the raw data */}
        <section className="alerts-section" style={{ gridColumn: '1 / -1' }}>
          <h2>Active Alerts</h2>
          <div className="alerts-list">
            {alerts.map((alert) => (
              <div key={alert.id} className={`alert-card severity-${alert.severity}`}>
                <div className="alert-header">
                  <h3>{alert.title}</h3>
                  <span className="timestamp">{alert.timestamp}</span>
                </div>
                <p>{alert.message}</p>
              </div>
            ))}
          </div>
        </section>

        {aiSummary && (
          <section className="ai-summary-section" style={{ gridColumn: '1 / -1' }}>
            <h2>AI Summary</h2>
            <div className="ai-summary-card card">
              <div className="ai-summary-text">
                <ReactMarkdown>{aiSummary}</ReactMarkdown>
              </div>
              <p className="ai-disclaimer">DoseWise does not diagnose or prescribe. All decisions are rule-based.</p>
            </div>
          </section>
        )}

        <section className="patient-profile-section">
          <h2>Patient Profile</h2>
          <div className="profile-card card">
            <p><strong>Name:</strong> {profile.name || '—'}</p>
            <p><strong>Age:</strong> {profile.age || '—'}</p>
            <p><strong>Conditions:</strong> {profile.conditions || '—'}</p>
            <p><strong>Medications:</strong> {medications.length ? medications.map((m) => m.name).join(', ') : '—'}</p>
          </div>
        </section>

        <section className="stats-cards">
          <div className="stat-card">
            <h3>Alert Severity</h3>
            <div className={`stat-value severity-${severity}`}>{severity}</div>
            <div className="stat-sub">{trendAlerts.length} trend alert(s)</div>
          </div>
          <div className="stat-card">
            <h3>Vitals (latest)</h3>
            <div className="stat-value">{latestBp || latestSugar ? 'Recorded' : '—'}</div>
            <div className="stat-sub">
              {latestBp ? `BP: ${latestBp}` : ''} {latestSugar ? `Sugar: ${latestSugar}` : ''}
            </div>
          </div>
          <div className="stat-card" style={{ gridColumn: '1 / -1' }}>
            <h3>Medication Inventory</h3>
            <InventoryStatus
              inventory={dashboard?.inventory || []}
              onInventoryUpdate={async () => {
                // Reload dashboard data after inventory update
                try {
                  const data = await api.getCaregiverDashboard();
                  setDashboard(data);
                } catch (e) {
                  console.error('Failed to reload dashboard:', e);
                }
              }}
            />
          </div>
          {/* Medication Timeline Card */}
          <div className="stat-card" style={{ gridColumn: '1 / -1' }}>
            <MedicationTimeline medications={dashboard?.medications || []} />
          </div>
          <div className="stat-card">
            <h3>Days with vitals</h3>
            <div className="stat-value">{dates.length}</div>
            <div className="stat-sub">daily reports</div>
          </div>
        </section>

        <section className="daily-reports-section">
          <h2>Daily reports (Intelligence layer)</h2>
          <p className="section-hint">Reports are generated from stored vitals each day. Select a date to view that day&apos;s report.</p>
          {dates.length === 0 ? (
            <p className="empty-state">No daily vitals yet. After the patient adds daily vitals, reports will appear here.</p>
          ) : (
            <>
              <div className="dates-list">
                {dates.map((d) => (
                  <button
                    key={d}
                    type="button"
                    className={`date-chip ${selectedDate === d ? 'active' : ''}`}
                    onClick={() => setSelectedDate(d)}
                  >
                    {d}
                  </button>
                ))}
              </div>
              {selectedReport && (
                <div className="report-card card">
                  <h3>Report for {selectedDate}</h3>
                  <div className="report-vitals">
                    <strong>Vitals recorded:</strong> {selectedReport.vitals?.length || 0} entries
                  </div>
                  {selectedReport.wellbeing?.length > 0 && (
                    <div className="report-wellbeing">
                      <strong>Wellbeing:</strong> {selectedReport.wellbeing.map((w) => w.feeling).join(', ')}
                    </div>
                  )}
                  {selectedReport.trend_alerts?.length > 0 && (
                    <div className="report-alerts">
                      <strong>Trend alerts:</strong>
                      <ul>
                        {selectedReport.trend_alerts.map((a, i) => (
                          <li key={i}>{a}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  <div className="report-summary">
                    <strong>AI Summary (for caregivers):</strong>
                    <div className="ai-summary-text">
                      <ReactMarkdown>{selectedReport.ai_summary || 'No alerts for this day.'}</ReactMarkdown>
                    </div>
                  </div>
                  <p className="ai-disclaimer">DoseWise does not diagnose or prescribe. All decisions are rule-based. This summary is for caregiver understanding only.</p>
                </div>
              )}
            </>
          )}
        </section>

      </div >

      <style jsx>{`
        .caregiver-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 1.5rem;
        }
        .caregiver-grid {
          display: grid;
          gap: 2rem;
          grid-template-columns: 1fr;
        }
        @media (min-width: 1024px) {
          .caregiver-grid {
            grid-template-columns: 2fr 1fr;
          }
          .stats-cards {
            grid-column: 1 / -1;
          }
        }
        .stats-cards {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: 1.5rem;
        }
        .stat-card {
          background: white;
          padding: 1.5rem;
          border-radius: var(--radius-lg);
          border: 1px solid var(--border-color);
          box-shadow: var(--shadow-sm);
        }
        .stat-card h3 {
          font-size: 0.875rem;
          color: var(--text-secondary);
          margin: 0 0 0.5rem 0;
          text-transform: uppercase;
          letter-spacing: 0.05em;
        }
        .stat-value {
          font-size: 2rem;
          font-weight: 700;
          color: var(--text-primary);
        }
        .severity-high,
        .severity-critical {
          color: var(--danger-color);
        }
        .severity-medium {
          color: var(--accent-color);
        }
        .profile-card p,
        .ai-summary-card p {
          margin: 0.5rem 0;
        }
        .section-hint,
        .empty-state {
          color: var(--text-secondary);
          font-size: 0.9rem;
          margin-bottom: 0.5rem;
        }
        .daily-reports-section .dates-list {
          display: flex;
          flex-wrap: wrap;
          gap: 0.5rem;
          margin-bottom: 1rem;
        }
        .date-chip {
          padding: 0.5rem 1rem;
          border-radius: var(--radius-md);
          border: 1px solid var(--border-color);
          background: white;
          cursor: pointer;
        }
        .date-chip.active {
          background: var(--primary-color);
          color: white;
          border-color: var(--primary-color);
        }
        .report-card {
          padding: 1rem;
        }
        .report-card h3 {
          margin-top: 0;
        }
        .report-vitals,
        .report-wellbeing,
        .report-alerts,
        .report-summary {
          margin: 0.75rem 0;
        }
        .ai-summary-text {
          line-height: 1.6;
          color: var(--text-secondary);
          white-space: pre-wrap;
        }
        .ai-summary-text h1 {
          font-size: 1.5rem;
          margin: 1rem 0 0.5rem 0;
          color: var(--text-primary);
          border-bottom: 2px solid var(--border-color);
          padding-bottom: 0.5rem;
        }
        .ai-summary-text h2 {
          font-size: 1.25rem;
          margin: 1.5rem 0 0.75rem 0;
          color: var(--text-primary);
        }
        .ai-summary-text h3 {
          font-size: 1.1rem;
          margin: 1rem 0 0.5rem 0;
          color: var(--text-primary);
        }
        .ai-summary-text p {
          margin: 0.5rem 0;
        }
        .ai-summary-text ul, .ai-summary-text ol {
          margin: 0.5rem 0;
          padding-left: 1.5rem;
        }
        .ai-summary-text li {
          margin: 0.25rem 0;
        }
        .ai-summary-text strong {
          color: var(--text-primary);
          font-weight: 600;
        }
        .ai-summary-text code {
          background: #f5f5f5;
          padding: 0.2rem 0.4rem;
          border-radius: 3px;
          font-family: monospace;
          font-size: 0.9em;
        }
        .ai-summary-text pre {
          background: #f5f5f5;
          padding: 1rem;
          border-radius: 6px;
          overflow-x: auto;
        }
        .upload-card {
          background: white;
          padding: 1.5rem;
        }
        .alert-card.severity-high {
          border-left: 4px solid var(--danger-color);
          background: #fef2f2;
        }
        .alert-card.severity-medium {
          border-left: 4px solid var(--accent-color);
          background: #fffbeb;
        }
        .alert-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
        }
        .alert-actions {
          display: flex;
          gap: 0.5rem;
          margin-top: 1rem;
        }
        .btn-small {
          padding: 0.5rem 1rem;
          font-size: 0.875rem;
          border-radius: var(--radius-md);
          background: white;
          border: 1px solid var(--border-color);
          cursor: pointer;
        }
        .btn-small:hover {
          background: #f8fafc;
        }
      `}</style>
    </div >
  );
}
