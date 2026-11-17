export async function streamChat({ message, sessionId, onMeta, onToken, onDone, onError }) {
  let response
  try {
    response = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, session_id: sessionId }),
    })
  } catch (e) { onError('Network error'); return }

  if (!response.ok) { onError(`Server error ${response.status}`); return }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const parts = buffer.split('\n\n')
    buffer = parts.pop()
    for (const part of parts) {
      const line = part.trim()
      if (!line.startsWith('data: ')) continue
      let payload
      try { payload = JSON.parse(line.slice(6)) } catch { continue }
      if (payload.type === 'meta')  onMeta(payload)
      if (payload.type === 'token') onToken(payload.text)
      if (payload.type === 'done')  onDone(payload)
    }
  }
}

export async function sendFeedback(interactionId, rating, comment = null) {
  await fetch('/api/feedback', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ interaction_id: interactionId, rating, comment }),
  })
}

export async function loadHistory(sessionId) {
  const r = await fetch(`/api/history/${sessionId}`)
  const d = await r.json()
  return d.messages || []
}