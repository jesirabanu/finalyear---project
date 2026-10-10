import { useState, useEffect } from 'react';
import { CheckCircle, AlertTriangle, RefreshCw } from 'lucide-react';

export default function StatusBadge() {
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchHealth = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('/api/health');
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      setHealth(data);
    } catch (err) {
      setError(err.message || 'Failed to connect to backend');
      setHealth(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let isMounted = true;

    const executeCheck = async () => {
      try {
        const response = await fetch('/api/health');
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        if (isMounted) {
          setHealth(data);
          setError(null);
        }
      } catch (err) {
        if (isMounted) {
          setError(err.message || 'Failed to connect to backend');
          setHealth(null);
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    executeCheck();
    const interval = setInterval(executeCheck, 30000);

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  return (
    <div className="status-badge-container">
      <div className="status-badge-header">
        <div className="status-indicator">
          {loading ? (
            <RefreshCw className="status-icon spin" size={16} />
          ) : error ? (
            <AlertTriangle className="status-icon text-danger" size={16} />
          ) : (
            <CheckCircle className="status-icon text-success" size={16} />
          )}
          <span className="status-title">
            {loading
              ? 'Checking Backend...'
              : error
              ? 'Backend Offline'
              : 'Backend Online'}
          </span>
        </div>
        <button
          type="button"
          className="btn-icon"
          onClick={fetchHealth}
          title="Refresh Backend Status"
          aria-label="Refresh Status"
        >
          <RefreshCw size={13} className={loading ? 'spin' : ''} />
        </button>
      </div>

      {health && (
        <div className="status-details">
          <div className="status-pill">
            <span className="pill-dot green"></span>
            <span>FastAPI: v{health.version}</span>
          </div>
          <div className="status-pill">
            <span
              className={`pill-dot ${
                health.integrations?.openrouteservice?.configured
                  ? 'green'
                  : 'yellow'
              }`}
            ></span>
            <span>
              ORS:{' '}
              {health.integrations?.openrouteservice?.configured
                ? 'Ready'
                : 'Key Pending'}
            </span>
          </div>
          <div className="status-pill">
            <span className="pill-dot green"></span>
            <span>Geocoding: Ready</span>
          </div>
          <div className="status-pill">
            <span className="pill-dot green"></span>
            <span>Open-Meteo: Live</span>
          </div>
        </div>
      )}

      {error && (
        <div className="status-error-msg">
          <span>Backend not reachable on port 8000. Start backend using <code>python run.py</code></span>
        </div>
      )}
    </div>
  );
}
