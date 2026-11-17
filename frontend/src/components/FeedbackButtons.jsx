import { useState } from 'react'
import { sendFeedback } from '../api/client'

export default function FeedbackButtons({ interactionId }) {
  const [sent, setSent] = useState(null)
  const submit = async (rating) => {
    setSent(rating)
    await sendFeedback(interactionId, rating)
  }
  if (sent) return <div className="feedback-thanks">Thanks for the feedback!</div>
  return (
    <div className="feedback">
      <button onClick={() => submit('up')} title="Helpful">Good</button>
      <button onClick={() => submit('down')} title="Not helpful">Bad</button>
    </div>
  )
}