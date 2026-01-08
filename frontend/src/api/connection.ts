import request from '@/utils/request'
import type { Connection, AccountConnectionSummary, PaginatedResponse } from '@/types'

export const connectionApi = {
  getList: (params?: object) =>
    request.get<any, PaginatedResponse<Connection>>('/api/connections/', { params }),

  getOnline: () =>
    request.get<any, Connection[]>('/api/connections/online/'),

  getStats: () =>
    request.get<any, { total: number; online: number; offline: number }>('/api/connections/stats/'),

  getByAccount: (params?: { status?: string }) =>
    request.get<any, { count: number; results: AccountConnectionSummary[] }>('/api/connections/by_account/', { params })
}
