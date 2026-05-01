<template>
  <div class="dashboard-container">
    <el-container>
      <el-header class="header">
        <div class="header-left">
          <el-icon class="logo-icon"><Monitor /></el-icon>
          <span class="title">服务器性能监控系统</span>
        </div>
        <div class="header-right">
          <el-badge :value="unreadAlerts.length" :hidden="unreadAlerts.length === 0" class="alert-badge">
            <el-button text @click="showAlertDialog = true">
              <el-icon><Bell /></el-icon>
            </el-button>
          </el-badge>
          <el-button text @click="showSettings = true">
            <el-icon><Setting /></el-icon>
          </el-button>
          <el-dropdown @command="handleCommand">
            <span class="user-info">
              <el-icon><User /></el-icon>
              <span>管理员</span>
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="history">历史记录</el-dropdown-item>
                <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      
      <el-main class="main-content">
        <div class="status-bar">
          <el-tag :type="wsConnected ? 'success' : 'danger'">
            <el-icon v-if="wsConnected"><Connection /></el-icon>
            <el-icon v-else><ConnectionOff /></el-icon>
            {{ wsConnected ? 'WebSocket 已连接' : 'WebSocket 断开' }}
          </el-tag>
          <span class="update-time">最后更新: {{ lastUpdateTime }}</span>
        </div>
        
        <el-row :gutter="20" class="metric-cards">
          <el-col :xs="12" :sm="12" :md="6">
            <el-card class="metric-card" :class="{ 'alert-card': currentMetrics.cpu_alert }">
              <div class="metric-header">
                <span class="metric-label">CPU 使用率</span>
                <el-icon class="metric-icon cpu-icon"><Cpu /></el-icon>
              </div>
              <div class="metric-value">
                <el-progress 
                  :percentage="currentMetrics.cpu_usage" 
                  :status="currentMetrics.cpu_alert ? 'exception' : ''"
                  :stroke-width="10"
                  :color="currentMetrics.cpu_alert ? '#f56c6c' : '#67c23a'"
                />
              </div>
              <div class="metric-detail">
                当前: {{ currentMetrics.cpu_usage.toFixed(1) }}%
              </div>
            </el-card>
          </el-col>
          
          <el-col :xs="12" :sm="12" :md="6">
            <el-card class="metric-card" :class="{ 'alert-card': currentMetrics.memory_alert }">
              <div class="metric-header">
                <span class="metric-label">内存使用率</span>
                <el-icon class="metric-icon memory-icon"><Coin /></el-icon>
              </div>
              <div class="metric-value">
                <el-progress 
                  :percentage="currentMetrics.memory_usage" 
                  :status="currentMetrics.memory_alert ? 'exception' : ''"
                  :stroke-width="10"
                  :color="currentMetrics.memory_alert ? '#f56c6c' : '#409eff'"
                />
              </div>
              <div class="metric-detail">
                当前: {{ currentMetrics.memory_usage.toFixed(1) }}%
              </div>
            </el-card>
          </el-col>
          
          <el-col :xs="12" :sm="12" :md="6">
            <el-card class="metric-card">
              <div class="metric-header">
                <span class="metric-label">磁盘使用率</span>
                <el-icon class="metric-icon disk-icon"><DataLine /></el-icon>
              </div>
              <div class="metric-value">
                <el-progress 
                  :percentage="currentMetrics.disk_usage" 
                  :stroke-width="10"
                  color="#e6a23c"
                />
              </div>
              <div class="metric-detail">
                当前: {{ currentMetrics.disk_usage.toFixed(1) }}%
              </div>
            </el-card>
          </el-col>
          
          <el-col :xs="12" :sm="12" :md="6">
            <el-card class="metric-card">
              <div class="metric-header">
                <span class="metric-label">网络流量</span>
                <el-icon class="metric-icon network-icon"><Upload /></el-icon>
              </div>
              <div class="network-values">
                <div class="network-item">
                  <el-icon class="up-icon"><Upload /></el-icon>
                  <span>{{ formatBytes(currentMetrics.network_sent) }}/s</span>
                </div>
                <div class="network-item">
                  <el-icon class="down-icon"><Download /></el-icon>
                  <span>{{ formatBytes(currentMetrics.network_recv) }}/s</span>
                </div>
              </div>
            </el-card>
          </el-col>
        </el-row>
        
        <el-row :gutter="20" class="chart-row">
          <el-col :xs="24" :lg="12">
            <el-card class="chart-card">
              <template #header>
                <div class="chart-header">
                  <span>CPU 使用率趋势</span>
                  <el-tag type="primary">实时</el-tag>
                </div>
              </template>
              <div ref="cpuChartRef" class="chart-container"></div>
            </el-card>
          </el-col>
          
          <el-col :xs="24" :lg="12">
            <el-card class="chart-card">
              <template #header>
                <div class="chart-header">
                  <span>内存使用率趋势</span>
                  <el-tag type="success">实时</el-tag>
                </div>
              </template>
              <div ref="memoryChartRef" class="chart-container"></div>
            </el-card>
          </el-col>
        </el-row>
      </el-main>
    </el-container>
    
    <el-dialog v-model="showAlertDialog" title="告警记录" width="600px">
      <el-table :data="alerts" v-loading="alertsLoading">
        <el-table-column prop="alert_type" label="类型" width="100">
          <template #default="{ row }">
            <el-tag :type="row.alert_type === 'cpu' ? 'danger' : 'warning'">
              {{ row.alert_type === 'cpu' ? 'CPU' : '内存' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="message" label="消息" />
        <el-table-column prop="value" label="当前值" width="100">
          <template #default="{ row }">
            {{ row.value.toFixed(1) }}%
          </template>
        </el-table-column>
        <el-table-column prop="is_read" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_read ? 'info' : 'danger'" size="small">
              {{ row.is_read ? '已读' : '未读' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="80">
          <template #default="{ row }">
            <el-button 
              v-if="!row.is_read" 
              type="primary" 
              link 
              size="small"
              @click="markRead(row.id)"
            >
              标记已读
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
    
    <el-dialog v-model="showSettings" title="告警阈值设置" width="400px">
      <el-form label-width="100px">
        <el-form-item label="CPU 阈值">
          <el-slider 
            v-model="tempThresholds.cpu_threshold" 
            :min="0" 
            :max="100"
            :step="5"
            show-input
          />
        </el-form-item>
        <el-form-item label="内存阈值">
          <el-slider 
            v-model="tempThresholds.memory_threshold" 
            :min="0" 
            :max="100"
            :step="5"
            show-input
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showSettings = false">取消</el-button>
        <el-button type="primary" @click="saveThresholds">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElNotification } from 'element-plus'
import * as echarts from 'echarts'
import {
  Monitor, Bell, Setting, User, ArrowDown, Connection, ConnectionOff,
  Cpu, Coin, DataLine, Upload, Download
} from '@element-plus/icons-vue'
import { useAuthStore } from '@/store/auth'
import { useMonitorStore } from '@/store/monitor'

const router = useRouter()
const authStore = useAuthStore()
const monitorStore = useMonitorStore()

const cpuChartRef = ref(null)
const memoryChartRef = ref(null)
let cpuChart = null
let memoryChart = null

const showAlertDialog = ref(false)
const showSettings = ref(false)
const alertsLoading = ref(false)
const tempThresholds = ref({
  cpu_threshold: 80,
  memory_threshold: 80
})

const currentMetrics = computed(() => monitorStore.currentMetrics)
const wsConnected = computed(() => monitorStore.wsConnected)
const alerts = computed(() => monitorStore.alerts)
const unreadAlerts = computed(() => monitorStore.unreadAlerts)
const cpuChartData = computed(() => monitorStore.cpuChartData)
const memoryChartData = computed(() => monitorStore.memoryChartData)
const thresholds = computed(() => monitorStore.thresholds)

const lastUpdateTime = computed(() => {
  if (currentMetrics.value.timestamp) {
    return new Date(currentMetrics.value.timestamp).toLocaleString('zh-CN')
  }
  return '--'
})

const formatBytes = (bytes) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const initCharts = () => {
  if (cpuChartRef.value) {
    cpuChart = echarts.init(cpuChartRef.value)
    const option = getChartOption('CPU 使用率 (%)', '#67c23a')
    cpuChart.setOption(option)
  }
  
  if (memoryChartRef.value) {
    memoryChart = echarts.init(memoryChartRef.value)
    const option = getChartOption('内存使用率 (%)', '#409eff')
    memoryChart.setOption(option)
  }
}

const getChartOption = (name, color) => {
  return {
    tooltip: {
      trigger: 'axis'
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: []
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 100,
      axisLabel: {
        formatter: '{value}%'
      }
    },
    series: [
      {
        name: name,
        type: 'line',
        smooth: true,
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: color },
            { offset: 1, color: 'rgba(255, 255, 255, 0.1)' }
          ])
        },
        lineStyle: {
          color: color,
          width: 2
        },
        itemStyle: {
          color: color
        },
        data: []
      }
    ]
  }
}

const updateCharts = () => {
  if (cpuChart) {
    cpuChart.setOption({
      xAxis: {
        data: cpuChartData.value.timestamps
      },
      series: [{
        data: cpuChartData.value.values
      }]
    })
  }
  
  if (memoryChart) {
    memoryChart.setOption({
      xAxis: {
        data: memoryChartData.value.timestamps
      },
      series: [{
        data: memoryChartData.value.values
      }]
    })
  }
}

const handleCommand = (command) => {
  switch (command) {
    case 'history':
      router.push('/history')
      break
    case 'logout':
      authStore.logout()
      monitorStore.disconnectWebSocket()
      monitorStore.clearChartData()
      ElMessage.success('已退出登录')
      router.push('/login')
      break
  }
}

const markRead = async (alertId) => {
  try {
    await monitorStore.markAlertRead(alertId)
    ElMessage.success('已标记为已读')
  } catch (error) {
    ElMessage.error('操作失败')
  }
}

const saveThresholds = async () => {
  try {
    await monitorStore.updateThresholds(tempThresholds.value)
    ElMessage.success('阈值设置已保存')
    showSettings.value = false
  } catch (error) {
    ElMessage.error('保存失败')
  }
}

watch(showAlertDialog, async (val) => {
  if (val) {
    alertsLoading.value = true
    try {
      await monitorStore.fetchAlerts()
    } catch (error) {
      console.error('获取告警失败:', error)
    } finally {
      alertsLoading.value = false
    }
  }
})

watch(showSettings, (val) => {
  if (val) {
    tempThresholds.value = { ...thresholds.value }
  }
})

watch([cpuChartData, memoryChartData], () => {
  console.log('图表数据更新, CPU 数据点:', cpuChartData.value.timestamps.length)
  updateCharts()
}, { deep: true })

watch(unreadAlerts, (newVal, oldVal) => {
  if (newVal.length > oldVal.length) {
    const latestAlert = newVal[0]
    const isRecovery = latestAlert.type?.includes('recovery')
    
    ElNotification({
      title: isRecovery ? '恢复通知' : '新告警',
      message: latestAlert.message,
      type: isRecovery ? 'success' : 'warning',
      duration: 5000
    })
  }
}, { deep: true })

onMounted(async () => {
  await monitorStore.fetchThresholds()
  await monitorStore.fetchCurrentMetrics()
  
  await nextTick()
  initCharts()
  
  updateCharts()
  
  monitorStore.connectWebSocket()
  
  window.addEventListener('resize', () => {
    cpuChart?.resize()
    memoryChart?.resize()
  })
})

onUnmounted(() => {
  cpuChart?.dispose()
  memoryChart?.dispose()
})
</script>

<style scoped>
.dashboard-container {
  min-height: 100vh;
}

.header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 30px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.logo-icon {
  font-size: 32px;
  color: white;
}

.title {
  font-size: 20px;
  font-weight: bold;
  color: white;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 15px;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  color: white;
  cursor: pointer;
  padding: 5px 10px;
  border-radius: 4px;
  transition: background 0.3s;
}

.user-info:hover {
  background: rgba(255, 255, 255, 0.1);
}

.main-content {
  padding: 20px;
}

.status-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.update-time {
  color: #909399;
  font-size: 14px;
}

.metric-cards {
  margin-bottom: 20px;
}

.metric-card {
  margin-bottom: 20px;
  transition: all 0.3s;
}

.metric-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.alert-card {
  border: 1px solid #f56c6c;
  background: rgba(245, 108, 108, 0.05);
}

.metric-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.metric-label {
  font-size: 14px;
  color: #909399;
}

.metric-icon {
  font-size: 24px;
}

.cpu-icon { color: #67c23a; }
.memory-icon { color: #409eff; }
.disk-icon { color: #e6a23c; }
.network-icon { color: #909399; }

.metric-value {
  margin-bottom: 10px;
}

.metric-detail {
  text-align: center;
  font-size: 14px;
  color: #606266;
}

.network-values {
  margin-top: 15px;
}

.network-item {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  font-size: 14px;
  color: #606266;
}

.up-icon { color: #67c23a; }
.down-icon { color: #409eff; }

.chart-row {
  margin-bottom: 20px;
}

.chart-card {
  margin-bottom: 20px;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chart-container {
  height: 350px;
  width: 100%;
}
</style>
