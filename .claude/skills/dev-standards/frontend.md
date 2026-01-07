# Vue 3 前端开发规范

## 1. 文件命名
| 类型 | 风格 | 示例 |
|------|------|------|
| 组件文件 | PascalCase | `AccountList.vue` |
| 视图文件 | PascalCase | `Dashboard.vue` |
| 工具函数 | camelCase | `formatDate.ts` |
| 样式文件 | kebab-case | `account-list.scss` |
| API 文件 | camelCase | `accountApi.ts` |

## 2. 组件结构
```vue
<script setup lang="ts">
// 1. 导入
import { ref, computed, onMounted } from 'vue'
import { useAccountStore } from '@/stores/account'
import type { Account } from '@/types'

// 2. Props & Emits
const props = defineProps<{
  accountId: number
}>()

const emit = defineEmits<{
  (e: 'update', account: Account): void
}>()

// 3. 状态
const loading = ref(false)
const store = useAccountStore()

// 4. 计算属性
const isActive = computed(() => store.currentAccount?.is_active)

// 5. 方法
const handleSubmit = async () => {
  loading.value = true
  try {
    await store.updateAccount(props.accountId)
    emit('update', store.currentAccount!)
  } finally {
    loading.value = false
  }
}

// 6. 生命周期
onMounted(() => {
  store.fetchAccount(props.accountId)
})
</script>

<template>
  <div class="account-detail">
    <!-- 模板内容 -->
  </div>
</template>

<style scoped lang="scss">
.account-detail {
  padding: 20px;
}
</style>
```

## 3. TypeScript 类型定义
```typescript
// types/account.ts
export interface Account {
  id: number
  username: string
  assigned_ip: string
  is_active: boolean
  created_at: string
}

export interface AccountCreateDTO {
  username: string
  password: string
  assigned_ip: string
}

export interface AccountListResponse {
  count: number
  results: Account[]
}
```

## 4. API 封装规范
```typescript
// api/account.ts
import request from '@/utils/request'
import type { Account, AccountCreateDTO, AccountListResponse } from '@/types'

export const accountApi = {
  getList: (params?: object) =>
    request.get<AccountListResponse>('/api/accounts/', { params }),

  getById: (id: number) =>
    request.get<Account>(`/api/accounts/${id}/`),

  create: (data: AccountCreateDTO) =>
    request.post<Account>('/api/accounts/', data),

  update: (id: number, data: Partial<AccountCreateDTO>) =>
    request.patch<Account>(`/api/accounts/${id}/`, data),

  delete: (id: number) =>
    request.delete(`/api/accounts/${id}/`)
}
```

## 5. Pinia Store 规范
```typescript
// stores/account.ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { accountApi } from '@/api/account'
import type { Account } from '@/types'

export const useAccountStore = defineStore('account', () => {
  // State
  const accounts = ref<Account[]>([])
  const loading = ref(false)
  const currentAccount = ref<Account | null>(null)

  // Getters
  const activeAccounts = computed(() =>
    accounts.value.filter(a => a.is_active)
  )

  // Actions
  const fetchAccounts = async () => {
    loading.value = true
    try {
      const res = await accountApi.getList()
      accounts.value = res.results
    } finally {
      loading.value = false
    }
  }

  return {
    accounts,
    loading,
    currentAccount,
    activeAccounts,
    fetchAccounts
  }
})
```

## 6. Element Plus 使用规范
- 按需导入组件
- 统一使用 ElMessage 提示
- 表格使用 ElTable + ElPagination 组合
- 表单验证使用 ElForm 内置验证

```typescript
// 消息提示
import { ElMessage, ElMessageBox } from 'element-plus'

// 成功提示
ElMessage.success('操作成功')

// 确认对话框
ElMessageBox.confirm('确定删除该账号?', '警告', {
  confirmButtonText: '确定',
  cancelButtonText: '取消',
  type: 'warning'
})
```

## 7. 样式规范
- 使用 SCSS 预处理器
- 组件样式使用 `scoped`
- 全局变量定义在 `styles/variables.scss`
- 遵循 BEM 命名: `.block__element--modifier`

```scss
// styles/variables.scss
$primary-color: #409eff;
$success-color: #67c23a;
$warning-color: #e6a23c;
$danger-color: #f56c6c;
$info-color: #909399;

$font-size-base: 14px;
$border-radius-base: 4px;
```

## 8. 路由规范
```typescript
// router/index.ts
import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    component: () => import('@/layouts/DefaultLayout.vue'),
    children: [
      {
        path: '',
        name: 'Dashboard',
        component: () => import('@/views/Dashboard.vue'),
        meta: { title: '看板' }
      },
      {
        path: 'accounts',
        name: 'Accounts',
        component: () => import('@/views/Accounts.vue'),
        meta: { title: '账号管理' }
      }
    ]
  }
]

export default createRouter({
  history: createWebHistory(),
  routes
})
```

## 9. 错误处理
```typescript
// utils/request.ts
import axios from 'axios'
import { ElMessage } from 'element-plus'

const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 10000
})

request.interceptors.response.use(
  response => response.data,
  error => {
    const message = error.response?.data?.detail || '请求失败'
    ElMessage.error(message)
    return Promise.reject(error)
  }
)

export default request
```
