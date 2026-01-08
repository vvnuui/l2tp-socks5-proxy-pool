import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { proxyApi, serverConfigApi } from '@/api/proxy'
import type { ProxyConfig } from '@/types'

export const useProxyStore = defineStore('proxy', () => {
  const proxies = ref<ProxyConfig[]>([])
  const loading = ref(false)
  const total = ref(0)
  const currentPage = ref(1)
  const pageSize = ref(20)
  const serverAddress = ref('服务器IP')

  const runningProxies = computed(() =>
    proxies.value.filter(p => p.is_running)
  )

  const fetchProxies = async (params?: object) => {
    loading.value = true
    try {
      const res = await proxyApi.getList({
        page: currentPage.value,
        page_size: pageSize.value,
        ...params
      })
      proxies.value = res.results
      total.value = res.count
    } finally {
      loading.value = false
    }
  }

  const startProxy = async (id: number) => {
    const res = await proxyApi.start(id)
    const index = proxies.value.findIndex(p => p.id === id)
    if (index !== -1) {
      proxies.value[index].is_running = true
      proxies.value[index].gost_pid = res.pid
      proxies.value[index].exit_ip = res.exit_ip || null
    }
    return res
  }

  const stopProxy = async (id: number) => {
    await proxyApi.stop(id)
    const index = proxies.value.findIndex(p => p.id === id)
    if (index !== -1) {
      proxies.value[index].is_running = false
      proxies.value[index].gost_pid = null
      proxies.value[index].exit_ip = null
    }
  }

  const restartProxy = async (id: number) => {
    const res = await proxyApi.restart(id)
    const index = proxies.value.findIndex(p => p.id === id)
    if (index !== -1) {
      proxies.value[index].is_running = true
      proxies.value[index].gost_pid = res.pid
      proxies.value[index].exit_ip = res.exit_ip || null
    }
    return res
  }

  const startAll = async () => {
    return await proxyApi.startAll()
  }

  const stopAll = async () => {
    return await proxyApi.stopAll()
  }

  const refreshExitIPs = async () => {
    return await proxyApi.refreshExitIPs()
  }

  const fetchServerAddress = async () => {
    try {
      const res = await serverConfigApi.get()
      serverAddress.value = res.server_address
    } catch {
      // 保持默认值
    }
  }

  return {
    proxies,
    loading,
    total,
    currentPage,
    pageSize,
    serverAddress,
    runningProxies,
    fetchProxies,
    startProxy,
    stopProxy,
    restartProxy,
    startAll,
    stopAll,
    refreshExitIPs,
    fetchServerAddress
  }
})
