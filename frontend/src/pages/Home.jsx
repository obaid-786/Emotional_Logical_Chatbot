import { Link } from 'react-router-dom'
export default function Home() {
  return (
    <>
      <nav className="nav">
        <div className="logo">🧠 MindfulAI</div>
        <div className="nav-links">
          <Link to="/chat">Chat</Link>
          <Link to="/analytics">Analytics</Link>
        </div>
      </nav>
      <section className="hero">
        <h1>Emotion-Aware AI Support</h1>
        <p>Real-time sentiment triage, auto-escalation, streaming responses, and analytics — grounded in your knowledge base.</p>
        <Link to="/chat" className="btn-primary">Start Chatting →</Link>
      </section>
      <section className="features">
        <div className="feature-card"><h3>🧠 Smart Triage</h3>
          <p>One-call intent + emotion classification with confidence scoring.</p></div>
        <div className="feature-card"><h3>🚨 Auto Escalation</h3>
          <p>Angry complaints and low-confidence messages route to human handoff.</p></div>
        <div className="feature-card"><h3>📊 Live Analytics</h3>
          <p>Sentiment distribution, escalation rate, cost per message, feedback.</p></div>
      </section>
    </>
  )
}