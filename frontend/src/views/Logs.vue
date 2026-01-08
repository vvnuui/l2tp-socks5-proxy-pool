<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { logApi } from '@/api/log'
import { Refresh, Delete } from '@element-plus/icons-vue'
import type { SystemLog } from '@/types'

const logs = ref<SystemLog[]>([])
const loading = ref(false)
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const levelFilter = ref<string>('')
const typeFilter = ref<string>('')

const fetchLogs = async () => {
  loading.value = true
  try {
    const params: Record<string, any> = {
      page: currentPage.value,
      page_size: pageSize.value
    }
    if (levelFilter.value) {
      params.level = levelFilter.value
    }
    if (typeFilter.value) {
      params.log_type = typeFilter.value
    }
    const res = await logApi.getList(params)
    logs.value = res.results
    total.value = res.count
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchLogs()
})

const handlePageChange = (page: number) => {
  currentPage.value = page
  fetchLogs()
}

const handleFilterChange = () => {
  currentPage.value = 1
  fetchLogs()
}

const handleClearOld = async () => {
  try {
    const days = await ElMessageBox.prompt(
      '请输入要保留的天数（将删除更早的日志）',
      '清理旧日志',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        inputValue: '30',
        inputPattern: /^\d+$/,
        inputErrorMessage: '请输入有效的天数'
      }
    )
    const res = await logApi.clearOld(parseInt(days.value))
    ElMessage.success(`已删除 ${res.deleted} 条日志`)
    fetchLogs()
  } catch (e) {
    // 取消
  }
}

const getLevelType = (level: string) => {
  switch (level) {
    case 'error': return 'danger'
    case 'warning': return 'warning'
    case 'info': return 'success'
    case 'debug': return 'info'
    default: return 'info'
  }
}

const getLogTypeLabel = (type: string) => {
  const labels: Record<string, string> = {
    connection: '连接',
    proxy: '代理',
    routing: '路由',
    system: '系统',
    l2tp: 'L2TP'
  }
  return labels[type] || type
}
</script>

<template>
  <div class="logs">
    <div class="page-header">
      <h2 class="page-header__title">系统日志</h2>
      <div class="page-header__actions">
        <el-select
          v-model="levelFilter"
          placeholder="日志级别"
          clearable
          style="width: 120px; margin-right: 12px;"
          @change="handleFilterChange"
        >
          <el-option label="信息" value="info" />
          <el-option label="警告" value="warning" />
          <el-option label="错误" value="error" />
          <el-option label="调试" value="debug" />
        </el-select>
        <el-select
          v-model="typeFilter"
          placeholder="日志类型"
          clearable
          style="width: 120px; margin-right: 12px;"
          @change="handleFilterChange"
        >
          <el-option label="连接" value="connection" />
          <el-option label="代理" value="proxy" />
          <el-option label="路由" value="routing" />
          <el-option label="系统" value="system" />
          <el-option label="L2TP" value="l2tp" />
        </el-select>
        <el-button :icon="Refresh" @click="fetchLogs">刷新</el-button>
        <el-button type="danger" :icon="Delete" @click="handleClearOld">清理旧日志</el-button>
      </div>
    </div>

    <div class="card">
      <el-table
        :data="logs"
        v-loading="loading"
        stripe
        style="width: 100%"
      >
        <el-table-column label="时间" width="170">
          <template #default="{ row }">
            {{ new Date(row.created_at).toLocaleString() }}
          </template>
        </el-table-column>
        <el-table-column label="级别" width="80">
          <template #default="{ row }">
            <el-tag :type="getLevelType(row.level)" size="small">
              {{ row.level.toUpperCase() }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="类型" width="80">
          <template #default="{ row }">
            {{ getLogTypeLabel(row.log_type) }}
          </template>
        </el-table-column>
        <el-table-column prop="message" label="消息" show-overflow-tooltip />
        <el-table-column prop="username" label="账号" width="120">
          <template #default="{ row }">
            {{ row.username || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="interface" label="接口" width="80">
          <template #default="{ row }">
            {{ row.interface || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="详情" width="80">
          <template #default="{ row }">
            <el-popover
              v-if="row.details"
              placement="left"
              :width="300"
              trigger="click"
            >
              <template #reference>
                <el-button size="small" link>查看</el-button>
              </template>
              <pre style="font-size: 12px; max-height: 300px; overflow: auto;">{{ JSON.stringify(row.details, null, 2) }}</pre>
            </el-popover>
            <span v-else>-</span>
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
