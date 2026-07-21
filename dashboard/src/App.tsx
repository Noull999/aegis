import { useEffect, useState, useCallback } from 'react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

interface Agent {
  id: string
  name: string
  description: string | null
  is_active: boolean
  created_at: string
}

interface Action {
  id: string
  agent_id: string
  action_type: string
  payload: Record<string, any>
  context: Record<string, any>
  status: string
  decision: string | null
  risk_score: number | null
  created_at: string
  resolved_at: string | null
  resolution: Record<string, any> | null
}

interface AuditLog {
  id: string
  action_id: string | null
  event_type: string
  details: Record<string, any>
  timestamp: string
}

function App() {
  const [agents, setAgents] = useState<Agent[]>([])
  const [pendingActions, setPendingActions] = useState<Action[]>([])
  const [allActions, setAllActions] = useState<Action[]>([])
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchData = useCallback(async () => {
    try {
      const [agentsRes, pendingRes, allRes, auditRes] = await Promise.all([
        fetch(`${API_URL}/agents`).then((r) => (r.ok ? r.json() : [])),
        fetch(`${API_URL}/actions?status=pending&limit=50`).then((r) =>
          r.ok ? r.json() : []
        ),
        fetch(`${API_URL}/actions?limit=10`).then((r) =>
          r.ok ? r.json() : []
        ),
        fetch(`${API_URL}/audit?limit=20`).then((r) =>
          r.ok ? r.json() : []
        ),
      ])
      setAgents(agentsRes)
      setPendingActions(pendingRes)
      setAllActions(allRes)
      setAuditLogs(auditRes)
      setError(null)
    } catch (err) {
      setError('No se pudo conectar con el backend')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 3000)
    return () => clearInterval(interval)
  }, [fetchData])

  const handleApprove = async (actionId: string) => {
    const reason = window.prompt('Motivo de aprobación:', 'Aprobado desde dashboard')
    if (reason === null) return
    try {
      const res = await fetch(`${API_URL}/actions/${actionId}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason }),
      })
      if (!res.ok) throw new Error('Error al aprobar')
      await fetchData()
    } catch (err) {
      alert('Error al aprobar acción')
    }
  }

  const handleReject = async (actionId: string) => {
    const reason = window.prompt('Motivo de rechazo:', 'Rechazado desde dashboard')
    if (reason === null) return
    try {
      const res = await fetch(`${API_URL}/actions/${actionId}/reject`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason }),
      })
      if (!res.ok) throw new Error('Error al rechazar')
      await fetchData()
    } catch (err) {
      alert('Error al rechazar acción')
    }
  }

  const riskColor = (score: number | null) => {
    if (score === null) return '#6b7280'
    if (score >= 70) return '#dc2626'
    if (score >= 40) return '#d97706'
    return '#16a34a'
  }

  if (loading) return <p style={{ padding: '2rem' }}>Cargando...</p>

  return (
    <div style={{ padding: '2rem', fontFamily: 'sans-serif', maxWidth: '960px', margin: '0 auto' }}>
      <h1>🛡 Aegis Dashboard</h1>
      <p>Cola de aprobación de acciones de agentes.</p>

      {error && (
        <div style={{ background: '#fee2e2', color: '#991b1b', padding: '1rem', borderRadius: '6px', marginBottom: '1rem' }}>
          {error}
        </div>
      )}

      <section style={{ marginBottom: '2rem' }}>
        <h2>Agentes registrados ({agents.length})</h2>
        {agents.length === 0 ? (
          <p>No hay agentes registrados.</p>
        ) : (
          <ul>
            {agents.map((agent) => (
              <li key={agent.id}>
                <strong>{agent.name}</strong>{' '}
                {agent.is_active ? '(activo)' : '(inactivo)'}
                {agent.description && <em> — {agent.description}</em>}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section style={{ marginBottom: '2rem' }}>
        <h2>Acciones pendientes ({pendingActions.length})</h2>
        {pendingActions.length === 0 ? (
          <p>No hay acciones esperando aprobación.</p>
        ) : (
          <div style={{ display: 'grid', gap: '1rem' }}>
            {pendingActions.map((action) => (
              <div
                key={action.id}
                style={{
                  border: '1px solid #e5e7eb',
                  borderRadius: '8px',
                  padding: '1rem',
                  background: '#fff',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <strong>{action.action_type}</strong>
                  <span style={{ fontSize: '0.85rem', color: '#6b7280' }}>
                    {new Date(action.created_at).toLocaleString()}
                  </span>
                </div>
                <pre style={{ background: '#f3f4f6', padding: '0.5rem', borderRadius: '4px', overflow: 'auto' }}>
                  {JSON.stringify(action.payload, null, 2)}
                </pre>
                <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.5rem' }}>
                  <button
                    onClick={() => handleApprove(action.id)}
                    style={{
                      background: '#10b981',
                      color: '#fff',
                      border: 'none',
                      padding: '0.5rem 1rem',
                      borderRadius: '4px',
                      cursor: 'pointer',
                    }}
                  >
                    Aprobar
                  </button>
                  <button
                    onClick={() => handleReject(action.id)}
                    style={{
                      background: '#ef4444',
                      color: '#fff',
                      border: 'none',
                      padding: '0.5rem 1rem',
                      borderRadius: '4px',
                      cursor: 'pointer',
                    }}
                  >
                    Rechazar
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      <section>
        <h2>Últimas acciones</h2>
        {allActions.length === 0 ? (
          <p>No hay acciones registradas.</p>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ background: '#f3f4f6', textAlign: 'left' }}>
                <th style={{ padding: '0.5rem' }}>Tipo</th>
                <th style={{ padding: '0.5rem' }}>Estado</th>
                <th style={{ padding: '0.5rem' }}>Decisión</th>
                <th style={{ padding: '0.5rem' }}>Riesgo</th>
                <th style={{ padding: '0.5rem' }}>Creado</th>
              </tr>
            </thead>
            <tbody>
              {allActions.map((action) => (
                <tr key={action.id} style={{ borderBottom: '1px solid #e5e7eb' }}>
                  <td style={{ padding: '0.5rem' }}>{action.action_type}</td>
                  <td style={{ padding: '0.5rem' }}>
                    <span
                      style={{
                        padding: '0.15rem 0.5rem',
                        borderRadius: '999px',
                        fontSize: '0.8rem',
                        fontWeight: 'bold',
                        background:
                          action.status === 'executed'
                            ? '#d1fae5'
                            : action.status === 'rejected'
                            ? '#fee2e2'
                            : action.status === 'pending'
                            ? '#fef3c7'
                            : '#e5e7eb',
                        color:
                          action.status === 'executed'
                            ? '#065f46'
                            : action.status === 'rejected'
                            ? '#991b1b'
                            : action.status === 'pending'
                            ? '#92400e'
                            : '#374151',
                      }}
                    >
                      {action.status}
                    </span>
                  </td>
                  <td style={{ padding: '0.5rem' }}>{action.decision || '-'}</td>
                  <td style={{ padding: '0.5rem', color: riskColor(action.risk_score), fontWeight: 'bold' }}>
                    {action.risk_score ?? '-'}
                  </td>
                  <td style={{ padding: '0.5rem' }}>
                    {new Date(action.created_at).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section>
        <h2>📋 Auditoría ({auditLogs.length} últimos eventos)</h2>
        {auditLogs.length === 0 ? (
          <p>No hay eventos de auditoría.</p>
        ) : (
          <div style={{ display: 'grid', gap: '0.75rem' }}>
            {auditLogs.map((log) => (
              <div
                key={log.id}
                style={{
                  border: '1px solid #e5e7eb',
                  borderRadius: '6px',
                  padding: '0.75rem',
                  background: '#f9fafb',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <strong>{log.event_type}</strong>
                  <span style={{ fontSize: '0.8rem', color: '#6b7280' }}>
                    {new Date(log.timestamp).toLocaleString()}
                  </span>
                </div>
                <div style={{ fontSize: '0.85rem', color: '#374151', marginTop: '0.25rem' }}>
                  action_id: {log.action_id || '-'}
                </div>
                <pre style={{ background: '#f3f4f6', padding: '0.5rem', borderRadius: '4px', overflow: 'auto', fontSize: '0.8rem' }}>
                  {JSON.stringify(log.details, null, 2)}
                </pre>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}

export default App
