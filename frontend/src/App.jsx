import { useEffect, useState } from 'react';

const API = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5001';

function tomorrow() {
  const day = new Date();
  day.setDate(day.getDate() + 1);
  return `${day.getFullYear()}-${String(day.getMonth() + 1).padStart(2, '0')}-${String(day.getDate()).padStart(2, '0')}`;
}

export default function App() {
  const [model, setModel] = useState(null);
  const [form, setForm] = useState({ origin: 'RDU', destination: 'JFK', date: tomorrow() });
  const [token, setToken] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [results, setResults] = useState(null);
  useEffect(() => {
    const controller = new AbortController();
    fetch(`${API}/api/model-status`, { signal: controller.signal })
      .then(response => { if (!response.ok) throw new Error(); return response.json(); })
      .then(setModel).catch(error => { if (error.name !== 'AbortError') setModel({ unavailable: true }); });
    return () => controller.abort();
  }, []);
  async function predict(event) {
    event.preventDefault();
    setBusy(true);
    setError('');
    setResults(null);
    try {
      const response = await fetch(`${API}/api/predict-live`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
        body: JSON.stringify(form),
      });
      const body = await response.json();
      if (!response.ok) throw new Error(body.error || 'Prediction unavailable.');
      setResults(body.predictions);
    } catch (error) {
      setError(error.message || 'Unable to reach the prediction service.');
    } finally {
      setBusy(false);
    }
  }
  return <main>
    <header><a className="brand" href="#">AeroPredict <span>FLIGHT INTELLIGENCE</span></a><span className="status">{model === null ? 'Connecting…' : model.unavailable ? 'Backend offline' : model.available ? 'Model ready' : 'Training required'}</span></header>
    <section className="intro"><p className="eyebrow">HISTORICAL EVIDENCE. FLIGHT-LEVEL ESTIMATES.</p><h1>Know the delay.<br /><span>Plan the arrival.</span></h1><p>Predict arrival delay minutes for US domestic flights using flight history and airport weather.</p></section>
    <section className="workflow" aria-label="Prediction architecture">
      <article><span className="step">01 / TRAINING</span><h2>Learn from the past</h2><p>BTS flight records + hourly weather → XGBoost regression.</p></article>
      <article><span className="step">02 / PREDICTION</span><h2>Estimate the next arrival</h2><p>Flight schedules + forecast weather → estimated delay minutes.</p></article>
    </section>
    <section className="search-panel"><div><p className="eyebrow">LIVE PREDICTION</p><h2>Find your flight</h2><p>Search a nonstop route. Results depend on schedule and weather coverage.</p></div>
      <form onSubmit={predict}>
        <div className="form-row">
          <label>From<InputCode value={form.origin} onChange={value => setForm({ ...form, origin: value })} /></label>
          <label>To<InputCode value={form.destination} onChange={value => setForm({ ...form, destination: value })} /></label>
          <label>Departure date<input type="date" required value={form.date} onChange={event => setForm({ ...form, date: event.target.value })} /></label>
          <button type="submit" disabled={busy || !model?.available}>{busy ? 'Predicting…' : 'Predict delay →'}</button>
        </div>
        <details><summary>Server access</summary><label>Access token, if required<input type="password" autoComplete="off" value={token} onChange={event => setToken(event.target.value)} /></label></details>
      </form>
      {model && !model.available && !model.unavailable && <p className="notice">The prediction model needs to be trained on your historical data before searching. Follow the project setup guide.</p>}
      {error && <p role="alert" className="notice error">{error}</p>}
    </section>
    <section aria-live="polite" className="results">
      {results?.length === 0 && <p className="notice">No matching flights were returned for this route and date.</p>}
      {results?.map((flight, index) => <article className="flight" key={`${flight.flight_number}-${flight.scheduled_dep_utc}-${index}`}>
        <div><p className="eyebrow">{flight.origin} → {flight.destination}</p><h2>{flight.flight_number}</h2><p>{flight.scheduled_departure_local || flight.scheduled_dep_utc}</p></div>
        {flight.status === 'ok' ? <><div className="estimate"><strong>{Math.abs(Math.round(flight.predicted_arrival_delay_minutes))}</strong><span>minutes {flight.predicted_arrival_delay_minutes < 0 ? 'early' : 'late'}<small>Model estimate</small></span></div><p className="evidence">{flight.history_sample_count} matching recent flights used for the historical feature.{flight.evaluation_mae_minutes != null && ` Held-out average error: ${flight.evaluation_mae_minutes.toFixed(1)} minutes.`}</p></> : <p className="notice">{flight.error || 'A prediction is unavailable for this flight.'}</p>}
      </article>)}
    </section>
    <footer>Predictions are estimates, not confirmed airline delays. Historical weather evaluation can be more optimistic than results using future forecasts.</footer>
  </main>;
}

function InputCode({ value, onChange }) {
  return <input required pattern="[A-Za-z]{3}" maxLength={3} value={value} onChange={event => onChange(event.target.value.toUpperCase())} placeholder="IATA code" />;
}
