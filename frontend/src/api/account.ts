import request from '@/utils/request'
import type { Account, AccountCreateDTO, PaginatedResponse } from '@/types'

export const accountApi = {
  getList: (params?: object) =>
    request.get<any, PaginatedResponse<Account>>('/api/accounts/', { params }),

  getById: (id: number) =>
    request.get<any, Account>(`/api/accounts/${id}/`),

  create: (data: AccountCreateDTO) =>
    request.post<any, Account>('/api/accounts/', data),

  update: (id: number, data: Partial<AccountCreateDTO>) =>
    request.patch<any, Account>(`/api/accounts/${id}/`, data),

  delete: (id: number) =>
    request.delete(`/api/accounts/${id}/`),

  toggleActive: (id: number) =>
    request.post<any, { is_active: boolean }>(`/api/accounts/${id}/toggle_active/`),

  getStats: () =>
    request.get<any, { total: number; active: number; inactive: number; online: number }>('/api/accounts/stats/'),

  batchCreate: (count: number, prefix: string) =>
    request.post<any, { created: number; accounts: Account[] }>('/api/accounts/batch_create/', { count, prefix })
}
