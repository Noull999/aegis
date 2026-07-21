import { useEffect, useState } from 'react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

interface Agent {
  id: string
  name: string
  description: string | null
  is_active: boolean
  created_at: string
}

function App() {
  const [agents, setAgents] = useState<Agent[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`${API_URL}/agents`)
      .then((r) => r.json())
      .then((data) => setAgents(data))
      .catch((err) => console.error(err))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div style={{ padding: '2rem', fontFamily: 'sans-serif' }}>
      <h1>🛡 Aegis Dashboard</h1>
      <p>Dashboard de aprobación de acciones de agentes.</p>
      {loading ? (
        <p>Cargando agentes...</p>
      ) : (
        <>
          <h2>Agentes registrados ({agents.length})</h2>
          <ul>
            {agents.map((agent) => (
              <li key={agent.id}>
                <strong>{agent.name}</strong>{' '}
                {agent.is_active ? '(activo)' : '(inactivo)'}
                {agent.description && <em> — {agent.description}</em>}
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  )
}

export default App
