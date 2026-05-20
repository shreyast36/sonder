import { useParams } from 'react-router-dom'
import ChatRoom from '../components/ChatRoom'
import { useAuth } from '../hooks/useAuth'

export default function Chat() {
  const { sessionId } = useParams()
  const { user } = useAuth()
  if (!user || !sessionId) return null
  return (
    <ChatRoom
      sessionId={sessionId}
      selfId={user.uid}
      showImpersonateLink
    />
  )
}
