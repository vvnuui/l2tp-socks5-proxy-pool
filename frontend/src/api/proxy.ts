import request from '@/utils/request'
import type { ProxyConfig, PaginatedResponse } from '@/types'

export const proxyApi = {
  getList: (params?: object) =>
    request.get<any, PaginatedResponse<ProxyConfig>>('/api/proxies/', { params }),

  getById: (id: number) =>
    request.get<any, ProxyConfig>(`/api/proxies/${id}/`),

  create: (data: { account: number; listen_port?: number; auto_start?: boolean }) =>
    request.post<any, ProxyConfig>('/api/proxies/', data),

  update: (id: number, data: Partial<ProxyConfig>) =>
    request.patch<any, ProxyConfig>(`/api/proxies/${id}/`, data),

  delete: (id: number) =>
    request.delete(`/api/proxies/${id}/`),

  start: (id: number) =>
    request.post<any, { message: string; pid: number; port: number }>(`/api/proxies/${id}/start/`),

  stop: (id: number) =>
    request.post<any, { message: string }>(`/api/proxies/${id}/stop/`),

  restart: (id: number) =>
    request.post<any, { message: string; pid: number }>(`/api/proxies/${id}/restart/`),

  getStatus: (id: number) =>
    request.get<any, { port: number; running: boolean; pid: number | null }>(`/api/proxies/${id}/status/`),

  getRunning: () =>
    request.get<any, ProxyConfig[]>('/api/proxies/running/'),

  startAll: () =>
    request.post<any, { started: number; failed: number }>('/api/proxies/start_all/'),

  stopAll: () =>
    request.post<any, { stopped: number }>('/api/proxies/stop_all/')
}
