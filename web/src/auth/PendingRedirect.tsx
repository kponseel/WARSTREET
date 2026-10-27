import { useEffect } from 'react'
import { useNavigate } from 'react-router'
import { peekPendingPath, takePendingPath } from '../lib/auth'
import { useAuth } from './context'

/** After a login (link or code), goes back to the page the player wanted (e.g. a join link). */
export function PendingRedirect() {
  const { session } = useAuth()
  const navigate = useNavigate()
  useEffect(() => {
    if (!session || !peekPendingPath()) return
    const path = takePendingPath()
    if (path) void navigate(path, { replace: true })
  }, [session, navigate])
  return null
}
