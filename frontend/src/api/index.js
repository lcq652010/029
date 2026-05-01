import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
})

api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

api.interceptors.response.use(
  (response) => {
    return response.data
  },
  (error) => {
    if (error.response) {
      switch (error.response.status) {
        case 401:
          localStorage.removeItem('token')
          window.location.href = '/login'
          break
        case 403:
          console.error('没有权限访问')
          break
        case 404:
          console.error('请求的资源不存在')
          break
        case 500:
          console.error('服务器错误')
          break
      }
    }
    return Promise.reject(error)
  }
)

export const authApi = {
  login: (username, password) => {
    const formData = new URLSearchParams()
    formData.append('username', username)
    formData.append('password', password)
    return api.post('/login', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    })
  },
  register: (username, password) => {
    return api.post('/register', { username, password })
  },
  getCurrentUser: () => {
    return api.get('/users/me')
  }
}

export const metricsApi = {
  getCurrent: () => {
    return api.get('/metrics/current')
  },
  getHistory: (params = {}) => {
    return api.get('/metrics/history', { params })
  }
}

export const alertsApi = {
  getAlerts: (unreadOnly = false, limit = 100) => {
    return api.get('/alerts', { params: { unread_only: unreadOnly, limit } })
  },
  markAsRead: (alertId) => {
    return api.put(`/alerts/${alertId}/read`)
  }
}

export const thresholdsApi = {
  getThresholds: () => {
    return api.get('/thresholds')
  },
  updateThresholds: (data) => {
    return api.put('/thresholds', data)
  }
}

export default api
