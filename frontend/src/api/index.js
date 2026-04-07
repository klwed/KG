import axios from 'axios'

const api = axios.create({
  baseURL: 'http://localhost:8000/api',
  timeout: 300000
})

api.interceptors.request.use(config => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  response => response.data,
  error => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default api

export const authApi = {
  login: (username, password) => api.post('/auth/login', { username, password }),
  register: (data) => api.post('/auth/register', data),
  getMe: () => api.get('/auth/me'),
  getRoleCheck: () => api.get('/auth/role-check'),
  createInviteCode: (role) => api.post('/auth/invite/create', { role }),
  listInviteCodes: () => api.get('/auth/invite/list'),
  deleteInviteCode: (code) => api.delete(`/auth/invite/${code}`)
}

export const documentApi = {
  upload: (file) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/document/process', formData)
  },
  list: () => api.get('/document/list')
}

export const extractApi = {
  extract: (filePath) => api.post('/extract', { file_path: filePath }),
  extractAll: () => api.post('/extract/all'),
  getTable: (limit) => api.get('/extract/table', { params: { limit } })
}

export const kgApi = {
  import: (triples) => api.post('/kg/import', { triples }),
  importFile: (filePath) => api.post('/kg/import/file', { file_path: filePath }),
  clear: () => api.delete('/kg/clear'),
  getStats: () => api.get('/kg/stats'),
  getGraph: (limit) => api.get('/kg/graph', { params: { limit } }),
  search: (keyword, limit) => api.get('/kg/search', { params: { keyword, limit } }),
  export: () => 'http://localhost:8000/api/kg/export',
  getSubgraph: (keyword, depth = 2) => api.get('/kg/subgraph', { params: { keyword, depth } }),
  getCtGraph: (ct) => api.get('/kg/ct-graph', { params: { ct_dimension: ct } }),
  getEntityDetails: (name) => api.get(`/kg/entity/${encodeURIComponent(name)}`)
}

export const qaApi = {
  ask: (question, useKgOnly = false, sessionId = null, history = null, username = null) => 
    api.post('/qa', { 
      question, 
      use_kg_only: useKgOnly,
      session_id: sessionId,
      conversation_history: history,
      username: username
    })
}

export const studentApi = {
  upload: (file) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/student/upload', formData)
  },
  getSummary: () => api.get('/student/summary'),
  importToKG: () => api.post('/student/import'),
  getReport: () => api.get('/student/report'),
  getMyScores: (username) => api.get('/student/my-scores', { params: { username } })
}
