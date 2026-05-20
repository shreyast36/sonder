import { useParams } from 'react-router-dom'
import ChatRoom from '../components/ChatRoom'

/**
 * Second-window view. Authenticates as the synthetic co-traveller so the
 * developer can reply to themselves and exercise the real-time pipeline.
 * Backend rejects this auth path unless LOCAL_MODE=true.
 */
export default function ChatAsFake() {
  const { sessionId, profileId } = useParams()
  if (!sessionId || !profileId) return null
  return (
    <ChatRoom
      sessionId={sessionId}
      selfId={profileId}
      impersonateProfileId={profileId}
    />
  )
}
