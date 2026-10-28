import { useNavigate } from 'react-router'
import { Tutorial } from './Tutorial'

/** The Help link: the same tutorial, then back to where the player was. */
export function TutorialPage() {
  const navigate = useNavigate()
  return (
    <Tutorial
      onDone={() => {
        const state: unknown = window.history.state
        const idx = typeof state === 'object' && state !== null && 'idx' in state ? state.idx : 0
        if (typeof idx === 'number' && idx > 0) void navigate(-1)
        else void navigate('/')
      }}
    />
  )
}
