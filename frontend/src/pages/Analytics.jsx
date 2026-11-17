import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Doughnut, Bar } from 'react-chartjs-2'
import { Chart, ArcElement, BarElement, CategoryScale, LinearScale, Tooltip, Legend } from 'chart.js'
Chart.register(ArcElement, BarElement, CategoryScale, LinearScale, Tooltip, Legend)

const COLORS = ['#ef4444','#f97316','#eab308','#3b82f6','#8b5cf6','#10b981','#94a3b8']

export default function Analytics() {
  const [data, setData] = useState(null)
  useEffect(() => {
    fetch('/api/analytics').then(r => r.json()).then(setData).catch(() => {})
  }, [])
  if (!data) return <div className="loading">Loading analytics…</div>

  const doughnut = {
    labels: data.by_emotion.map(e => e.emotion),
    datasets: [{ data: data.by_emotion.map(e => e.count), backgroundColor: COLORS }],
  }
  const bar = {
    labels: data.by_intent.map(i => i.intent),
    datasets: [{ label: 'Messages', data: data.by_intent.map(i => i.count), backgroundColor: '#6366f1' }],
  }

  return (
    <div className="analytics-page">
      <h1>Analytics Dashboard</h1>
      <div className="stats">
        <div className="stat"><div className="stat-value">{data.total}</div>
          <div className="stat-label">Total Messages</div></div>
        <div className="stat"><div className="stat-value">{(data.escalation_rate*100).toFixed(1)}%</div>
          <div className="stat-label">Escalation Rate</div></div>
        <div className="stat"><div className="stat-value">${data.total_cost_usd.toFixed(4)}</div>
          <div className="stat-label">Total LLM Cost</div></div>
        <div className="stat"><div className="stat-value">{data.feedback.up || 0} / {data.feedback.down || 0}</div>
          <div className="stat-label">👍 / 👎</div></div>
      </div>
      <div className="charts">
        <div className="chart-card"><h3>By Emotion</h3><Doughnut data={doughnut} /></div>
        <div className="chart-card"><h3>By Intent</h3><Bar data={bar} /></div>
      </div>
      {data.recent_negative_feedback.length > 0 && (
        <div className="chart-card">
          <h3>Recent Negative Feedback</h3>
          <ul className="neg-feedback">
            {data.recent_negative_feedback.map((f, i) => (
              <li key={i}><b>{f.emotion}</b> · {f.route} — {f.comment || '(no comment)'}</li>
            ))}
          </ul>
        </div>
      )}
      <Link to="/chat" className="btn-ghost" style={{marginTop:'20px'}}>← Back to Chat</Link>
    </div>
  )
}