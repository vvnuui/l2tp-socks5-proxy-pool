import request from '@/utils/request'
import type { SystemLog, PaginatedResponse } from '@/types'

export const logApi = {
  getList: (params?: object) =>
    request.get<any, PaginatedResponse<SystemLog>>('/api/logs/', { params }),

  getRecent: (limit: number = 50) =>
    request.get<any, SystemLog[]>('/api/logs/recent/', { params: { limit } }),

  getErrors: (limit: number = 50) =>
    request.get<any, SystemLog[]>('/api/logs/errors/', { params: { limit } }),

  getByType: () =>
    request.get<any, { log_type: string; count: number }[]>('/api/logs/by_type/'),

  clearOld: (days: number = 30) =>
    request.delete<any, { deleted: number }>('/api/logs/clear_old/', { params: { days } })
}
