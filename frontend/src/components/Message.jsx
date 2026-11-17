import FeedbackButtons from './FeedbackButtons'

export default function Message({ role, text, meta, streaming, interactionId }) {
  return (
    <div className={`message ${role}`}>
      <div className="bubble">
        {text}
        {streaming && <span className="cursor">▍</span>}
      </div>
      {meta && (
        <div className="meta-tag">
          <span className={`emotion ${meta.emotion}`}>{meta.emotion}</span>
          <span className={`strategy ${meta.strategy}`}>{meta.strategy}</span>
          <span>{(meta.confidence * 100).toFixed(0)}%</span>
        </div>
      )}
      {role === 'bot' && !streaming && interactionId && (
        <FeedbackButtons interactionId={interactionId} />
      )}
    </div>
  )
}