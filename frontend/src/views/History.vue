<template>
  <div class="history-container">
    <el-container>
      <el-header class="header">
        <div class="header-left">
          <el-icon class="logo-icon"><Monitor /></el-icon>
          <span class="title">服务器性能监控系统</span>
        </div>
        <div class="header-right">
          <el-button type="primary" @click="goBack">
            <el-icon><ArrowLeft /></el-icon>
            返回监控
          </el-button>
        </div>
      </el-header>
      
      <el-main class="main-content">
        <el-card class="filter-card">
          <template #header>
            <div class="filter-header">
              <span>查询条件</span>
            </div>
          </template>
          <el-form :inline="true" :model="queryForm" class="query-form">
            <el-form-item label="开始时间">
              <el-date-picker
                v-model="queryForm.startTime"
                type="datetime"
                placeholder="选择开始时间"
                format="YYYY-MM-DD HH:mm:ss"
                value-format="YYYY-MM-DDTHH:mm:ss"
              />
            </el-form-item>
            <el-form-item label="结束时间">
              <el-date-picker
                v-model="queryForm.endTime"
                type="datetime"
                placeholder="选择结束时间"
                format="YYYY-MM-DD HH:mm:ss"
                value-format="YYYY-MM-DDTHH:mm:ss"
              />
            </el-form-item>
            <el-form-item label="每页条数">
              <el-select v-model="queryForm.limit" style="width: 120px">
                <el-option :label="50" :value="50" />
                <el-option :label="100" :value="100" />
                <el-option :label="200" :value="200" />
                <el-option :label="500" :value="500" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="handleQuery" :loading="loading">
                <el-icon><Search /></el-icon>
                查询
              </el-button>
              <el-button @click="handleReset">
                <el-icon><Refresh /></el-icon>
                重置
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
        
        <el-row :gutter="20" class="chart-row">
          <el-col :xs="24" :lg="12">
            <el-card class="chart-card">
              <template #header>
                <div class="chart-header">
                  <span>CPU 使用率历史趋势</span>
                </div>
              </template>
              <div ref="cpuChartRef" class="chart-container"></div>
            </el-card>
          </el-col>
          
          <el-col :xs="24" :lg="12">
            <el-card class="chart-card">
              <template #header>
                <div class="chart-header">
                  <span>内存使用率历史趋势</span>
                </div>
              </template>
              <div ref="memoryChartRef" class="chart-container"></div>
            </el-card>
          </el-col>
        </el-row>
        
        <el-card class="table-card">
          <template #header>
            <div class="table-header">
              <span>详细数据列表</span>
              <el-tag type="info">共 {{ total }} 条记录</el-tag>
            </div>
          </template>
          
          <el-table
            :data="historyData"
            v-loading="loading"
            stripe
            style="width: 100%"
          >
            <el-table-column
              prop="timestamp"
              label="时间"
              width="180"
              :formatter="formatTimestamp"
            />
            <el-table-column prop="cpu_usage" label="CPU 使用率" width="150">
              <template #default="{ row }">
                <el-progress
                  :percentage="row.cpu_usage"
                  :stroke-width="10"
                  :color="row.cpu_usage >= 80 ? '#f56c6c' : '#67c23a'"
                />
              </template>
            </el-table-column>
            <el-table-column prop="memory_usage" label="内存使用率" width="150">
              <template #default="{ row }">
                <el-progress
                  :percentage="row.memory_usage"
                  :stroke-width="10"
                  :color="row.memory_usage >= 80 ? '#f56c6c' : '#409eff'"
                />
              </template>
            </el-table-column>
            <el-table-column prop="disk_usage" label="磁盘使用率" width="150">
              <template #default="{ row }">
                <span>{{ row.disk_usage.toFixed(1) }}%</span>
              </template>
            </el-table-column>
            <el-table-column prop="network_sent" label="网络上行" width="120">
              <template #default="{ row }">
                <span>{{ formatBytes(row.network_sent) }}/s</span>
              </template>
            </el-table-column>
            <el-table-column prop="network_recv" label="网络下行" width="120">
              <template #default="{ row }">
                <span>{{ formatBytes(row.network_recv) }}/s</span>
              </template>
            </el-table-column>
          </el-table>
          
          <el-pagination
            v-model:current-page="queryForm.page"
            v-model:page-size="queryForm.limit"
            :page-sizes="[50, 100, 200, 500]"
            :total="total"
            layout="total, sizes, prev, pager, next, jumper"
            @size-change="handleSizeChange"
            @current-change="handleCurrentChange"
            style="margin-top: 20px; justify-content: flex-end"
          />
        </el-card>
      </el-main>
    </el-container>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'
import {
  Monitor, ArrowLeft, Search, Refresh
} from '@element-plus/icons-vue'
import { useMonitorStore } from '@/store/monitor'

const router = useRouter()
const monitorStore = useMonitorStore()

const cpuChartRef = ref(null)
const memoryChartRef = ref(null)
let cpuChart = null
let memoryChart = null

const loading = ref(false)
const total = ref(0)

const queryForm = reactive({
  startTime: null,
  endTime: null,
  page: 1,
  limit: 100
})

const historyData = ref([])

const goBack = () => {
  router.push('/dashboard')
}

const formatTimestamp = (row) => {
  if (!row.timestamp) return '--'
  return new Date(row.timestamp).toLocaleString('zh-CN')
}

const formatBytes = (bytes) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
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
      data: [],
      axisLabel: {
        rotate: 45,
        formatter: (value) => {
          return value.split(' ')[1] || value
        }
      }
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 100,
      axisLabel: {
        formatter: '{value}%'
      }
    },
    dataZoom: [
      {
        type: 'inside',
        start: 0,
        end: 100
      },
      {
        type: 'slider',
        start: 0,
        end: 100,
        height: 20,
        bottom: 10
      }
    ],
    series: [
      {
        name: name,
        type: 'line',
        smooth: true,
        sampling: 'lttb',
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

const updateCharts = () => {
  const timestamps = historyData.value.map(item => {
    return new Date(item.timestamp).toLocaleString('zh-CN')
  }).reverse()
  
  const cpuValues = historyData.value.map(item => item.cpu_usage).reverse()
  const memoryValues = historyData.value.map(item => item.memory_usage).reverse()
  
  if (cpuChart) {
    cpuChart.setOption({
      xAxis: {
        data: timestamps
      },
      series: [{
        data: cpuValues
      }]
    })
  }
  
  if (memoryChart) {
    memoryChart.setOption({
      xAxis: {
        data: timestamps
      },
      series: [{
        data: memoryValues
      }]
    })
  }
}

const handleQuery = async () => {
  loading.value = true
  try {
    const params = {
      limit: queryForm.limit,
      offset: (queryForm.page - 1) * queryForm.limit
    }
    
    if (queryForm.startTime) {
      params.start_time = queryForm.startTime
    }
    if (queryForm.endTime) {
      params.end_time = queryForm.endTime
    }
    
    const data = await monitorStore.fetchMetricsHistory(params)
    historyData.value = data
    total.value = data.length < queryForm.limit 
      ? (queryForm.page - 1) * queryForm.limit + data.length 
      : queryForm.page * queryForm.limit + 1
    
    if (data.length > 0) {
      updateCharts()
    }
  } catch (error) {
    console.error('查询历史数据失败:', error)
  } finally {
    loading.value = false
  }
}

const handleReset = () => {
  queryForm.startTime = null
  queryForm.endTime = null
  queryForm.page = 1
  queryForm.limit = 100
  handleQuery()
}

const handleSizeChange = (val) => {
  queryForm.limit = val
  queryForm.page = 1
  handleQuery()
}

const handleCurrentChange = (val) => {
  queryForm.page = val
  handleQuery()
}

watch(historyData, () => {
  if (historyData.value.length > 0) {
    updateCharts()
  }
})

onMounted(async () => {
  await nextTick()
  initCharts()
  handleQuery()
  
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
.history-container {
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

.main-content {
  padding: 20px;
}

.filter-card {
  margin-bottom: 20px;
}

.filter-header {
  font-weight: bold;
}

.query-form {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.chart-row {
  margin-bottom: 20px;
}

.chart-card {
  margin-bottom: 20px;
}

.chart-header {
  font-weight: bold;
}

.chart-container {
  height: 350px;
  width: 100%;
}

.table-card {
  margin-bottom: 20px;
}

.table-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: bold;
}
</style>
