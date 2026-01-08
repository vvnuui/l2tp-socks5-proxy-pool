<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { useDashboardStore } from '@/stores/dashboard'
import { User, Connection, Setting, Document } from '@element-plus/icons-vue'

const store = useDashboardStore()
const refreshTimer = ref<number | null>(null)

onMounted(() => {
  store.fetchData()
  // 每 30 秒刷新一次
  refreshTimer.value = window.setInterval(() => {
    store.fetchData()
  }, 30000)
})

onUnmounted(() => {
  if (refreshTimer.value) {
    clearInterval(refreshTimer.value)
  }
})
</script>

<template>
  <div class="dashboard" v-loading="store.loading">
    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stat-row">
      <el-col :span="6">
        <div class="stat-card">
          <div class="stat-card__icon stat-card__icon--primary">
            <el-icon><User /></el-icon>
          </div>
          <div class="stat-card__content">
            <div class="stat-card__value">{{ store.stats.accounts_total }}</div>
            <div class="stat-card__label">总账号数</div>
          </div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card">
          <div class="stat-card__icon stat-card__icon--success">
            <el-icon><Connection /></el-icon>
          </div>
          <div class="stat-card__content">
            <div class="stat-card__value">{{ store.stats.connections_online }}</div>
            <div class="stat-card__label">在线连接</div>
          </div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card">
          <div class="stat-card__icon stat-card__icon--warning">
            <el-icon><Setting /></el-icon>
          </div>
          <div class="stat-card__content">
            <div class="stat-card__value">{{ store.stats.proxies_running }}</div>
            <div class="stat-card__label">运行代理</div>
          </div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card">
          <div class="stat-card__icon stat-card__icon--danger">
            <el-icon><Document /></el-icon>
          </div>
          <div class="stat-card__content">
            <div class="stat-card__value">{{ store.pppInterfaces.length }}</div>
            <div class="stat-card__label">PPP 接口</div>
          </div>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="20">
      <!-- PPP 接口状态 -->
      <el-col :span="12">
        <div class="card">
          <div class="card__header">
            <span class="card__title">PPP 接口</span>
            <el-button size="small" @click="store.fetchData">刷新</el-button>
          </div>
          <el-table :data="store.pppInterfaces" stripe size="small" style="width: 100%">
            <el-table-column prop="name" label="接口名">
              <template #default="{ row }">
                {{ row }}
              </template>
            </el-table-column>
            <el-table-column label="状态" width="100">
              <template #default>
                <span class="status-tag status-tag--online">在线</span>
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-if="store.pppInterfaces.length === 0" description="暂无 PPP 接口" />
        </div>
      </el-col>

      <!-- 最近连接 -->
      <el-col :span="12">
        <div class="card">
          <div class="card__header">
            <span class="card__title">最近连接</span>
            <router-link to="/connections">
              <el-button size="small" type="primary" link>查看全部</el-button>
            </router-link>
          </div>
          <el-table :data="store.recentConnections" stripe size="small" style="width: 100%">
            <el-table-column prop="username" label="用户名" />
            <el-table-column prop="interface" label="接口" width="80" />
            <el-table-column prop="local_ip" label="IP 地址" width="120" />
            <el-table-column label="连接时间" width="100">
              <template #default="{ row }">
                {{ new Date(row.connected_at).toLocaleTimeString() }}
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-if="store.recentConnections.length === 0" description="暂无连接" />
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped lang="scss">
.dashboard {
  .stat-row {
    margin-bottom: 20px;
  }
}
</style>
