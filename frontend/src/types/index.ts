// 账号相关类型
export interface Account {
  id: number
  username: string
  password?: string
  assigned_ip: string
  is_active: boolean
  remark: string
  is_online: boolean
  current_interface: string | null
  proxy_port: number | null
  proxy_running: boolean
  created_at: string
  updated_at: string
}

export interface AccountCreateDTO {
  username: string
  password: string
  assigned_ip?: string
  is_active?: boolean
  remark?: string
  auto_assign_ip?: boolean
  auto_create_proxy?: boolean
}

// 连接相关类型
export interface Connection {
  id: number
  account: number
  username: string
  assigned_ip: string
  interface: string
  peer_ip: string
  local_ip: string
  status: 'online' | 'offline'
  duration: number
  bytes_sent: number
  bytes_received: number
  connected_at: string
  disconnected_at: string | null
}

// 账号连接汇总类型
export interface AccountConnectionSummary {
  account_id: number
  username: string
  assigned_ip: string
  interface: string
  peer_ip: string
  local_ip: string
  status: 'online' | 'offline'
  duration: number
  connected_at: string | null
  disconnected_at: string | null
  total_bytes_sent: number
  total_bytes_received: number
  connection_count: number
}

// 代理配置相关类型
export interface ProxyConfig {
  id: number
  account: number
  username: string
  assigned_ip: string
  listen_port: number
  is_running: boolean
  gost_pid: number | null
  exit_ip: string | null
  auto_start: boolean
  is_online: boolean
  created_at: string
  updated_at: string
}

// 路由表相关类型
export interface RoutingTable {
  id: number
  account: number
  username: string
  table_id: number
  table_name: string
  interface: string
  is_active: boolean
  created_at: string
  updated_at: string
}

// 系统日志相关类型
export interface SystemLog {
  id: number
  level: 'info' | 'warning' | 'error' | 'debug'
  log_type: 'connection' | 'proxy' | 'routing' | 'system' | 'l2tp'
  message: string
  details: Record<string, any> | null
  account: number | null
  username: string | null
  ip_address: string | null
  interface: string
  created_at: string
}

// 看板统计类型
export interface DashboardStats {
  accounts_total: number
  accounts_active: number
  connections_online: number
  proxies_running: number
}

export interface DashboardData {
  stats: DashboardStats
  ppp_interfaces: string[]
  recent_connections: {
    id: number
    username: string
    interface: string
    local_ip: string
    connected_at: string
  }[]
}

// 服务器配置类型
export interface ServerConfig {
  domain: string
  public_ip: string | null
  private_ip: string | null
  server_address: string
  updated_at: string
}

// 分页响应类型
export interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

// API 响应类型
export interface ApiResponse<T> {
  data: T
  message?: string
}
