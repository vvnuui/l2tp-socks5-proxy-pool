import request from '@/utils/request'
import type { DashboardData } from '@/types'

export const dashboardApi = {
  getData: () =>
    request.get<any, DashboardData>('/api/dashboard/')
}
