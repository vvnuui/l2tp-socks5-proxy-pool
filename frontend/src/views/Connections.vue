<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { connectionApi } from '@/api/connection'
import { Refresh } from '@element-plus/icons-vue'
import type { Connection } from '@/types'

const connections = ref<Connection[]>([])
const loading = ref(false)
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const statusFilter = ref<string>('')
const refreshTimer = ref<number | null>(null)

const fetchConnections = async () => {
  loading.value = true
  try {
    const params: Record<string, any> = {
      page: currentPage.value,
      page_size: pageSize.value
    }
    if (statusFilter.value) {
      params.status = statusFilter.value
    }
    const res = await connectionApi.getList(params)
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
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const handlePageChange = (page: number) => {
  currentPage.value = page
  fetchConnections()
}

const handleFilterChange = () => {
  currentPage.value = 1
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
        <el-table-column prop="username" label="用户名" min-width="100" />
        <el-table-column prop="interface" label="接口" width="80" />
        <el-table-column prop="local_ip" label="本地 IP" width="120" />
        <el-table-column prop="peer_ip" label="对端 IP" width="120" />
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <span :class="['status-tag', `status-tag--${row.status}`]">
              {{ row.status === 'online' ? '在线' : '离线' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="连接时长" width="110">
          <template #default="{ row }">
            {{ formatDuration(row.duration) }}
          </template>
        </el-table-column>
        <el-table-column label="发送流量" width="100">
          <template #default="{ row }">
            {{ formatBytes(row.bytes_sent) }}
          </template>
        </el-table-column>
        <el-table-column label="接收流量" width="100">
          <template #default="{ row }">
            {{ formatBytes(row.bytes_received) }}
          </template>
        </el-table-column>
        <el-table-column label="连接时间" min-width="160">
          <template #default="{ row }">
            {{ new Date(row.connected_at).toLocaleString() }}
          </template>
        </el-table-column>
        <el-table-column label="断开时间" min-width="160">
          <template #default="{ row }">
            {{ row.disconnected_at ? new Date(row.disconnected_at).toLocaleString() : '-' }}
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next"
          @current-change="handlePageChange"
        />
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
</style>
