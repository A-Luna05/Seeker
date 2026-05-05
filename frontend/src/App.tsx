import { useEffect } from 'react'
import { pingHealth } from './api/client'
import { SearchAgentPanel } from './components/SearchAgentPanel'

function App() {
  useEffect(() => {
    pingHealth()
  }, [])

  return (
    <main className="min-h-screen">
      <SearchAgentPanel />
    </main>
  )
}

export default App
