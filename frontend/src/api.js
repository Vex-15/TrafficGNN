const BASE = '/api'

async function request(path, options = {}) {
  const response = await fetch(`${BASE}${path}`, options)
  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`
    try {
      const body = await response.json()
      if (body?.detail) {
        detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
      }
    } catch {
      /* non-JSON error body */
    }
    throw new Error(detail)
  }
  if (response.status === 204) return null
  return response.json()
}

const json = (method, body) => ({
  method,
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
})

export const api = {
  health: () => request('/health'),
  schema: () => request('/schema'),

  listProjects: () => request('/projects'),
  getProject: (id) => request(`/projects/${id}`),
  createProject: (payload) => request('/projects', json('POST', payload)),
  createDemo: () => request('/demo', { method: 'POST' }),
  deleteProject: (id) => request(`/projects/${id}`, { method: 'DELETE' }),

  uploadTemplate: (id, file) => {
    const form = new FormData()
    form.append('file', file)
    return request(`/projects/${id}/template`, { method: 'POST', body: form })
  },
  updateSections: (id, sections) =>
    request(`/projects/${id}/template/sections`, json('PATCH', { sections })),
  confirmTemplate: (id) => request(`/projects/${id}/template/confirm`, { method: 'POST' }),

  uploadSources: (id, files) => {
    const form = new FormData()
    files.forEach((file) => form.append('files', file))
    return request(`/projects/${id}/sources`, { method: 'POST', body: form })
  },
  deleteSource: (id, sourceId) =>
    request(`/projects/${id}/sources/${sourceId}`, { method: 'DELETE' }),

  patchRecord: (id, recordId, payload) =>
    request(`/projects/${id}/records/${recordId}`, json('PATCH', payload)),
  approveSafe: (id) => request(`/projects/${id}/records/approve-safe`, { method: 'POST' }),

  resolveDuplicate: (id, duplicateId, action) =>
    request(`/projects/${id}/duplicates/${duplicateId}`, json('POST', { action })),
  resolveConflict: (id, conflictId, recordId) =>
    request(`/projects/${id}/conflicts/${conflictId}`, json('POST', { record_id: recordId })),

  generate: (id, payload) => request(`/projects/${id}/generate`, json('POST', payload)),
}

export const formatBytes = (bytes) => {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  const exponent = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1)
  return `${(bytes / 1024 ** exponent).toFixed(exponent ? 1 : 0)} ${units[exponent]}`
}

export const statusMeta = {
  auto: { label: 'Auto-approved', tone: 'emerald' },
  verified: { label: 'Verified', tone: 'emerald' },
  review: { label: 'Needs review', tone: 'amber' },
  manual: { label: 'Manual entry', tone: 'rose' },
  unverified: { label: 'Unclassified', tone: 'slate' },
  duplicate: { label: 'Duplicate', tone: 'slate' },
  conflict: { label: 'Conflict', tone: 'rose' },
}

export const toneClasses = {
  emerald: 'bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200/70',
  amber: 'bg-amber-50 text-amber-700 ring-1 ring-amber-200/70',
  rose: 'bg-rose-50 text-rose-700 ring-1 ring-rose-200/70',
  slate: 'bg-slate-100 text-slate-600 ring-1 ring-slate-200',
  brand: 'bg-brand-50 text-brand-700 ring-1 ring-brand-100',
}
