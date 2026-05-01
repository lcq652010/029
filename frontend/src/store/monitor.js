import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { metricsApi, alertsApi, thresholdsApi } from '@/api'

export const useMonitorStore = defineStore('monitor', () => {
  const currentMetrics = ref({
    timestamp: null,
    cpu_usage: 0,
    memory_usage: 0,
    disk_usage: 0,
    network_sent: 0,
    network_recv: 0,
    cpu_alert: false,
    memory_alert: false
  })

  const metricsHistory = ref([])
  const alerts = ref([])
  const thresholds = ref({
    cpu_threshold: 80,
    memory_threshold: 80
  })

  const wsConnected = ref(false)
  const ws = ref(null)

  const unreadAlerts = computed(() => {
    return alerts.value.filter(alert => !alert.is_read)
  })

  const cpuChartData = ref({
    timestamps: [],
    values: []
  })

  const memoryChartData = ref({
    timestamps: [],
    values: []
  })

  function updateCurrentMetrics(metrics) {
    currentMetrics.value = { ...currentMetrics.value, ...metrics }
    
    const time = new Date(metrics.timestamp)
    const timeStr = time.toLocaleTimeString()
    
    cpuChartData.value.timestamps.push(timeStr)
    cpuChartData.value.values.push(metrics.cpu_usage)
    
    memoryChartData.value.timestamps.push(timeStr)
    memoryChartData.value.values.push(metrics.memory_usage)
    
    const maxPoints = 60
    if (cpuChartData.value.timestamps.length > maxPoints) {
      cpuChartData.value.timestamps.shift()
      cpuChartData.value.values.shift()
    }
    if (memoryChartData.value.timestamps.length > maxPoints) {
      memoryChartData.value.timestamps.shift()
      memoryChartData.value.values.shift()
    }
  }

  async function fetchCurrentMetrics() {
    try {
      const metrics = await metricsApi.getCurrent()
      updateCurrentMetrics(metrics)
      return metrics
    } catch (error) {
      console.error('获取当前指标失败:', error)
      throw error
    }
  }

  async function fetchMetricsHistory(params = {}) {
    try {
      const history = await metricsApi.getHistory(params)
      metricsHistory.value = history
      return history
    } catch (error) {
      console.error('获取历史指标失败:', error)
      throw error
    }
  }

  async function fetchAlerts(unreadOnly = false) {
    try {
      const alertsData = await alertsApi.getAlerts(unreadOnly)
      alerts.value = alertsData
      return alertsData
    } catch (error) {
      console.error('获取告警失败:', error)
      throw error
    }
  }

  async function markAlertRead(alertId) {
    try {
      await alertsApi.markAsRead(alertId)
      const alert = alerts.value.find(a => a.id === alertId)
      if (alert) {
        alert.is_read = true
      }
      return true
    } catch (error) {
      console.error('标记告警已读失败:', error)
      throw error
    }
  }

  async function fetchThresholds() {
    try {
      const data = await thresholdsApi.getThresholds()
      thresholds.value = data
      return data
    } catch (error) {
      console.error('获取阈值失败:', error)
      throw error
    }
  }

  async function updateThresholds(data) {
    try {
      const result = await thresholdsApi.updateThresholds(data)
      thresholds.value = {
        cpu_threshold: result.cpu_threshold,
        memory_threshold: result.memory_threshold
      }
      return result
    } catch (error) {
      console.error('更新阈值失败:', error)
      throw error
    }
  }

  function connectWebSocket() {
    if (ws.value && ws.value.readyState === WebSocket.OPEN) {
      return
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/ws/metrics`
    
    ws.value = new WebSocket(wsUrl)

    ws.value.onopen = () => {
      console.log('WebSocket 连接成功')
      wsConnected.value = true
    }

    ws.value.onclose = () => {
      console.log('WebSocket 连接关闭')
      wsConnected.value = false
      setTimeout(() => {
        connectWebSocket()
      }, 3000)
    }

    ws.value.onerror = (error) => {
      console.error('WebSocket 错误:', error)
      wsConnected.value = false
    }

    ws.value.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data)
        console.log('收到 WebSocket 消息:', message.type)
        
        if (message.type === 'metrics') {
          updateCurrentMetrics(message.data)
        } else if (message.type === 'alert') {
          const newAlert = {
            ...message.data,
            timestamp: message.timestamp,
            is_read: false
          }
          alerts.value.unshift(newAlert)
        } else if (message.type === 'pong') {
          console.log('收到 pong 响应')
        }
      } catch (error) {
        console.error('解析 WebSocket 消息失败:', error)
      }
    }
  }

  function disconnectWebSocket() {
    if (ws.value) {
      ws.value.close()
      ws.value = null
    }
    wsConnected.value = false
  }

  function clearChartData() {
    cpuChartData.value = { timestamps: [], values: [] }
    memoryChartData.value = { timestamps: [], values: [] }
  }

  return {
    currentMetrics,
    metricsHistory,
    alerts,
    thresholds,
    wsConnected,
    unreadAlerts,
    cpuChartData,
    memoryChartData,
    fetchCurrentMetrics,
    fetchMetricsHistory,
    fetchAlerts,
    markAlertRead,
    fetchThresholds,
    updateThresholds,
    connectWebSocket,
    disconnectWebSocket,
    clearChartData
  }
})
