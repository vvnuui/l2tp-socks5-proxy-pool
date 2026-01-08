<script setup lang="ts">
import { onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useProxyStore } from '@/stores/proxy'
import { Refresh, VideoPlay, VideoPause, RefreshRight, Position } from '@element-plus/icons-vue'

const store = useProxyStore()

onMounted(() => {
  store.fetchProxies()
  store.fetchServerAddress()
})

const handleStart = async (id: number) => {
  try {
    await store.startProxy(id)
    ElMessage.success('代理已启动')
  } catch (e) {
    // 错误已处理
  }
}

const handleStop = async (id: number) => {
  try {
    await store.stopProxy(id)
    ElMessage.success('代理已停止')
  } catch (e) {
    // 错误已处理
  }
}

const handleRestart = async (id: number) => {
  try {
    await store.restartProxy(id)
    ElMessage.success('代理已重启')
  } catch (e) {
    // 错误已处理
  }
}

const handleStartAll = async () => {
  try {
    await ElMessageBox.confirm(
      '确定要启动所有可用的代理吗？',
      '确认',
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'info' }
    )
    const res = await store.startAll()
    ElMessage.success(`已启动 ${res.started} 个代理`)
    store.fetchProxies()
  } catch (e) {
    // 取消或错误
  }
}

const handleStopAll = async () => {
  try {
    await ElMessageBox.confirm(
      '确定要停止所有运行中的代理吗？',
      '警告',
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }
    )
    const res = await store.stopAll()
    ElMessage.success(`已停止 ${res.stopped} 个代理`)
    store.fetchProxies()
  } catch (e) {
    // 取消或错误
  }
}

const handleRefreshExitIPs = async () => {
  try {
    const res = await store.refreshExitIPs()
    ElMessage.success(`已更新 ${res.updated} 个出口 IP`)
    store.fetchProxies()
  } catch (e) {
    // 错误已处理
  }
}

const handlePageChange = (page: number) => {
  store.currentPage = page
  store.fetchProxies()
}

const copyToClipboard = (text: string) => {
  navigator.clipboard.writeText(text)
  ElMessage.success('已复制到剪贴板')
}
</script>

<template>
  <div class="proxies">
    <div class="page-header">
      <h2 class="page-header__title">代理管理</h2>
      <div class="page-header__actions">
        <el-button :icon="Refresh" @click="store.fetchProxies()">刷新</el-button>
        <el-button :icon="Position" @click="handleRefreshExitIPs">刷新出口IP</el-button>
        <el-button type="success" :icon="VideoPlay" @click="handleStartAll">全部启动</el-button>
        <el-button type="danger" :icon="VideoPause" @click="handleStopAll">全部停止</el-button>
      </div>
    </div>

    <div class="card">
      <el-table
        :data="store.proxies"
        v-loading="store.loading"
        stripe
        style="width: 100%"
      >
        <el-table-column prop="listen_port" label="监听端口" width="100">
          <template #default="{ row }">
            <el-link type="primary" @click="copyToClipboard(String(row.listen_port))">
              {{ row.listen_port }}
            </el-link>
          </template>
        </el-table-column>
        <el-table-column prop="username" label="绑定账号" width="130" />
        <el-table-column label="出口 IP" width="140">
          <template #default="{ row }">
            <el-link
              v-if="row.exit_ip"
              type="primary"
              @click="copyToClipboard(row.exit_ip)"
            >
              {{ row.exit_ip }}
            </el-link>
            <span v-else class="text-muted">{{ row.is_running ? '检测中...' : '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="账号状态" width="100">
          <template #default="{ row }">
            <span :class="['status-tag', row.is_online ? 'status-tag--online' : 'status-tag--offline']">
              {{ row.is_online ? '在线' : '离线' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="代理状态" width="100">
          <template #default="{ row }">
            <span :class="['status-tag', row.is_running ? 'status-tag--running' : 'status-tag--stopped']">
              {{ row.is_running ? '运行中' : '已停止' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="gost_pid" label="进程 PID" width="100">
          <template #default="{ row }">
            {{ row.gost_pid || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="自动启动" width="100">
          <template #default="{ row }">
            <el-tag :type="row.auto_start ? 'success' : 'info'" size="small">
              {{ row.auto_start ? '是' : '否' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="连接地址" min-width="200">
          <template #default="{ row }">
            <el-link
              type="primary"
              @click="copyToClipboard(`socks5://${store.serverAddress}:${row.listen_port}`)"
            >
              socks5://{{ store.serverAddress }}:{{ row.listen_port }}
            </el-link>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <div class="table-actions">
              <el-button
                v-if="!row.is_running"
                size="small"
                type="success"
                :icon="VideoPlay"
                :disabled="!row.is_online"
                @click="handleStart(row.id)"
              >
                启动
              </el-button>
              <el-button
                v-else
                size="small"
                type="danger"
                :icon="VideoPause"
                @click="handleStop(row.id)"
              >
                停止
              </el-button>
              <el-button
                size="small"
                :icon="RefreshRight"
                :disabled="!row.is_online"
                @click="handleRestart(row.id)"
              >
                重启
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="store.currentPage"
          :page-size="store.pageSize"
          :total="store.total"
          layout="total, prev, pager, next"
          @current-change="handlePageChange"
        />
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.text-muted {
  color: #909399;
}
</style>
