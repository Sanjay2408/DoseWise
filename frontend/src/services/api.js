import axios from 'axios';
import { getToken, clearSession, setSession } from './auth';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Attach the auth token to every request
apiClient.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// On session expiry (401), clear the session and send the user to the login page
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error?.response?.status;
    const isAuthCall = String(error?.config?.url || '').startsWith('/auth/');
    if (status === 401 && !isAuthCall) {
      clearSession();
      if (window.location.pathname !== '/login') {
        window.location.assign('/login');
      }
    }
    return Promise.reject(error);
  }
);

// Turn an API error into a plain-language message safe to show on screen.
export function friendlyError(error, fallback) {
  if (!error?.response) {
    return "We couldn't reach the server — check your internet connection and try again.";
  }
  const detail = error.response.data?.detail;
  if (typeof detail === 'string' && detail.length < 200) {
    return detail;
  }
  return fallback || 'Something went wrong. Please try again.';
}

function deviceTimeISO() {
  // Return ISO string with local timezone offset instead of UTC
  const now = new Date();
  const offset = -now.getTimezoneOffset(); // offset in minutes
  const offsetHours = Math.floor(Math.abs(offset) / 60).toString().padStart(2, '0');
  const offsetMinutes = (Math.abs(offset) % 60).toString().padStart(2, '0');
  const offsetSign = offset >= 0 ? '+' : '-';

  const year = now.getFullYear();
  const month = (now.getMonth() + 1).toString().padStart(2, '0');
  const day = now.getDate().toString().padStart(2, '0');
  const hours = now.getHours().toString().padStart(2, '0');
  const minutes = now.getMinutes().toString().padStart(2, '0');
  const seconds = now.getSeconds().toString().padStart(2, '0');
  const ms = now.getMilliseconds().toString().padStart(3, '0');

  return `${year}-${month}-${day}T${hours}:${minutes}:${seconds}.${ms}${offsetSign}${offsetHours}:${offsetMinutes}`;
}

const api = {
  // --- Auth ---
  register: async ({ email, name, password }) => {
    const response = await apiClient.post('/auth/register', { email, name, password });
    setSession(response.data.token, response.data.user);
    return response.data;
  },

  login: async ({ email, password }) => {
    const response = await apiClient.post('/auth/login', { email, password });
    setSession(response.data.token, response.data.user);
    return response.data;
  },

  logout: () => {
    clearSession();
  },

  // --- Medications & State (device time sent so agent uses current time) ---
  getCurrentState: async () => {
    const response = await apiClient.get('/state', {
      params: { current_time: deviceTimeISO() },
    });
    return response.data;
  },

  getMedications: async () => {
    const response = await apiClient.get('/medications');
    return response.data;
  },

  deleteMedication: async (name) => {
    const response = await apiClient.delete(`/medications/${encodeURIComponent(name)}`);
    return response.data;
  },

  confirmDose: async (payload) => {
    let body = {};
    if (typeof payload === 'object' && payload !== null) {
      body = payload;
    } else if (typeof payload === 'number') {
      body = { medication_id: payload };
    } else {
      body = { medication_name: payload };
    }

    const response = await apiClient.post('/dose/confirm', body, {
      params: { current_time: deviceTimeISO() },
    });
    return response.data;
  },

  // --- Setup & Config ---
  submitSetup: async (setupData) => {
    const response = await apiClient.post('/setup', setupData);
    return response.data;
  },

  // --- Vitals ---
  submitVitals: async (vitalData) => {
    const response = await apiClient.post('/vitals', vitalData);
    return response.data;
  },

  getHealthTrends: async () => {
    const response = await apiClient.get('/vitals/trends');
    return response.data;
  },

  // --- Caregiver & Alerts (trend-aware intelligence) ---
  getAlerts: async () => {
    const response = await apiClient.get('/alerts');
    return response.data;
  },

  getCaregiverDashboard: async () => {
    const [stateRes, alertsRes, trendsRes] = await Promise.all([
      apiClient.get('/state', { params: { current_time: deviceTimeISO() } }),
      apiClient.get('/alerts'),
      apiClient.get('/vitals/trends'),
    ]);
    return {
      profile: stateRes.data.patient_profile || {},
      medications: stateRes.data.medications || [],
      inventory: stateRes.data.inventory || [],
      alerts: alertsRes.data.alerts || [],
      trend_alerts: alertsRes.data.trend_alerts || [],
      ai_summary: alertsRes.data.ai_summary || '',
      severity: alertsRes.data.severity || 'low',
      trends: trendsRes.data,
    };
  },

  runAgent: async () => {
    const response = await apiClient.post('/agent/run', {
      current_time: deviceTimeISO(),
    });
    return response.data;
  },

  getDailyReports: async () => {
    const response = await apiClient.get('/caregiver/daily-reports');
    return response.data;
  },

  // --- Images ---
  uploadMedicationImage: async (medicationId, file) => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await apiClient.post(`/medications/${medicationId}/image`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  searchPharmacy: async (medicationName) => {
    const response = await apiClient.post('/pharmacy/search', {
      medication_name: medicationName
    });
    return response.data;
  },

  // --- Inventory Update ---
  updateInventory: async (medicationName, quantity) => {
    const response = await apiClient.post('/inventory/update', {
      medication_name: medicationName,
      quantity: quantity
    });
    return response.data;
  },
};

export default api;
