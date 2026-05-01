import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/api'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '')
  const user = ref(null)

  const isAuthenticated = computed(() => !!token.value)

  async function login(username, password) {
    try {
      const response = await authApi.login(username, password)
      token.value = response.access_token
      localStorage.setItem('token', response.access_token)
      await fetchUserInfo()
      return true
    } catch (error) {
      console.error('登录失败:', error)
      throw error
    }
  }

  async function register(username, password) {
    try {
      await authApi.register(username, password)
      return true
    } catch (error) {
      console.error('注册失败:', error)
      throw error
    }
  }

  async function fetchUserInfo() {
    try {
      const user.value = await authApi.getCurrentUser()
    } catch (error) {
      console.error('获取用户信息失败:', error)
      logout()
      throw error
    }
  }

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem('token')
  }

  return {
    token,
    user,
    isAuthenticated,
    login,
    register,
    fetchUserInfo,
    logout
  }
})
