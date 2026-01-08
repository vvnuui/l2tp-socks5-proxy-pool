<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { connectionApi } from '@/api/connection'
import { Refresh } from '@element-plus/icons-vue'
import type { AccountConnectionSummary } from '@/types'

const connections = ref<AccountConnectionSummary[]>([])
const loading = ref(false)
const total = ref(0)
const statusFilter = ref<string>('')
const refreshTimer = ref<number | null>(null)

const fetchConnections = async () => {
  loading.value = true
  try {
    const params: Record<string, any> = {}
    if (statusFilter.value) {
      params.status = statusFilter.value
    }
    const res = await connectionApi.getByAccount(params)
    connections.value = res.results
    total.value = res.count
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchConnections()
  refreshTimer.value = window.setInterval(fetchConnections, 30000)
})

onUnmounted(() => {
  if (refreshTimer.value) {
    clearInterval(refreshTimer.value)
  }
})

const formatDuration = (seconds: number): string => {
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const secs = Math.floor(seconds % 60)

  if (hours > 0) {
    return `${hours}h ${minutes}m ${secs}s`
  }
  if (minutes > 0) {
    return `${minutes}m ${secs}s`
  }
  return `${secs}s`
}

const formatBytes = (bytes: number): string => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const handleFilterChange = () => {
  fetchConnections()
}
</script>

<template>
  <div class="connections">
    <div class="page-header">
      <h2 class="page-header__title">连接状态</h2>
      <div class="page-header__actions">
        <el-select
          v-model="statusFilter"
          placeholder="状态筛选"
          clearable
          style="width: 120px; margin-right: 12px;"
          @change="handleFilterChange"
        >
          <el-option label="在线" value="online" />
          <el-option label="离线" value="offline" />
        </el-select>
        <el-button :icon="Refresh" @click="fetchConnections">刷新</el-button>
      </div>
    </div>

    <div class="card">
      <el-table
        :data="connections"
        v-loading="loading"
        stripe
        style="width: 100%"
      >
        <el-table-column prop="username" label="用户名" width="120" />
        <el-table-column prop="interface" label="接口" width="80">
          <template #default="{ row }">
            {{ row.interface || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="local_ip" label="分配 IP" width="120">
          <template #default="{ row }">
            {{ row.local_ip || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <span :class="['status-tag', `status-tag--${row.status}`]">
              {{ row.status === 'online' ? '在线' : '离线' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="连接时长" width="110">
          <template #default="{ row }">
            {{ row.connected_at ? formatDuration(row.duration) : '-' }}
          </template>
        </el-table-column>
        <el-table-column label="发送流量" width="100">
          <template #default="{ row }">
            {{ formatBytes(row.total_bytes_sent) }}
          </template>
        </el-table-column>
        <el-table-column label="接收流量" width="100">
          <template #default="{ row }">
            {{ formatBytes(row.total_bytes_received) }}
          </template>
        </el-table-column>
        <el-table-column label="总流量" width="100">
          <template #default="{ row }">
            {{ formatBytes(row.total_bytes) }}
          </template>
        </el-table-column>
        <el-table-column label="连接次数" width="90">
          <template #default="{ row }">
            {{ row.connection_count }}
          </template>
        </el-table-column>
        <el-table-column label="最近连接时间" min-width="160">
          <template #default="{ row }">
            {{ row.connected_at ? new Date(row.connected_at).toLocaleString() : '-' }}
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrapper">
        <span class="total-info">共 {{ total }} 个账号</span>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.total-info {
  color: #909399;
  font-size: 14px;
}
</style>
