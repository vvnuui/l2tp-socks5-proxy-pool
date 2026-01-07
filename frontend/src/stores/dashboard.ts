import { defineStore } from 'pinia'
import { ref } from 'vue'
import { dashboardApi } from '@/api/dashboard'
import type { DashboardData, DashboardStats } from '@/types'

export const useDashboardStore = defineStore('dashboard', () => {
  const loading = ref(false)
  const stats = ref<DashboardStats>({
    accounts_total: 0,
    accounts_active: 0,
    connections_online: 0,
    proxies_running: 0
  })
  const pppInterfaces = ref<string[]>([])
  const recentConnections = ref<DashboardData['recent_connections']>([])

  const fetchData = async () => {
    loading.value = true
    try {
      const data = await dashboardApi.getData()
      stats.value = data.stats
      pppInterfaces.value = data.ppp_interfaces
      recentConnections.value = data.recent_connections
    } finally {
      loading.value = false
    }
  }

  return {
    loading,
    stats,
    pppInterfaces,
    recentConnections,
    fetchData
  }
})
