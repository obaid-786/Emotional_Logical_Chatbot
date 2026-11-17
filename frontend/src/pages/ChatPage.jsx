import { useState, useRef, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { streamChat, loadHistory } from '../api/client'
import Message from '../components/Message'

export default function ChatPage() {
  const [messages, setMessages] = useState([
    { role: 'bot', text: "Hi! I'm your emotion-aware assistant. How can I help?" }
  ])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const sessionId = useRef(localStorage.getItem('chat_sid') || 'sess-' + Math.random().toString(36).slice(2, 10))

  useEffect(() => {
    localStorage.setItem('chat_sid', sessionId.current)
    loadHistory(sessionId.current).then(hist => {
      if (hist.length) {
        const restored = hist.map(m => ({ role: m.role === 'user' ? 'user' : 'bot', text: m.content }))
        setMessages([{ role: 'bot', text: "Welcome back! Let's continue." }, ...restored])
      }
    }).catch(() => {})
  }, [])

  const send = async () => {
    const text = input.trim()
    if (!text || busy) return
    setInput(''); setBusy(true)

    setMessages(m => [...m, { role: 'user', text }])

    // placeholder bot message that will fill with tokens
    setMessages(m => [...m, { role: 'bot', text: '', streaming: true }])

    const appendToken = (token) => {
      setMessages(m => {
        const copy = [...m]
        copy[copy.length - 1] = { ...copy[copy.length - 1], text: copy[copy.length - 1].text + token }
        return copy
      })
    }
    const setMeta = (meta) => {
      setMessages(m => {
        const copy = [...m]
        copy[copy.length - 1] = { ...copy[copy.length - 1], meta }
        return copy
      })
    }
    const finish = (payload) => {
      setMessages(m => {
        const copy = [...m]
        copy[copy.length - 1] = {
          ...copy[copy.length - 1],
          streaming: false,
          interactionId: payload.interaction_id,
        }
        return copy
      })
      setBusy(false)
    }

    await streamChat({
      message: text, sessionId: sessionId.current,
      onMeta: setMeta, onToken: appendToken,
      onDone: finish, onError: (err) => {
        appendToken(`[Error: ${err}]`)
        setBusy(false)
      },
    })
  }

  return (
    <div className="chat-page">
      <div className="chat-header">
        <span>🤖 MindfulAI Assistant</span>
        <Link to="/analytics" className="btn-ghost">Analytics →</Link>
      </div>
      <div className="chat-messages">
        {messages.map((m, i) => <Message key={i} {...m} />)}
        {busy && !messages[messages.length-1]?.text && <div className="typing">● ● ●</div>}
      </div>
      <div className="chat-input">
        <input value={input} onChange={e => setInput(e.target.value)}
               onKeyDown={e => e.key === 'Enter' && send()}
               placeholder="Type your message..." disabled={busy} />
        <button onClick={send} disabled={busy}>Send</button>
      </div>
    </div>
  )
}