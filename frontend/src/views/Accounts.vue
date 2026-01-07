<script setup lang="ts">
import { onMounted, ref, reactive } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAccountStore } from '@/stores/account'
import { Plus, Delete, Edit, Refresh } from '@element-plus/icons-vue'
import type { Account, AccountCreateDTO } from '@/types'

const store = useAccountStore()

const dialogVisible = ref(false)
const dialogType = ref<'create' | 'edit'>('create')
const currentAccount = ref<Account | null>(null)

const form = reactive<AccountCreateDTO>({
  username: '',
  password: '',
  assigned_ip: '',
  is_active: true,
  remark: '',
  auto_assign_ip: true,
  auto_create_proxy: true
})

const resetForm = () => {
  form.username = ''
  form.password = ''
  form.assigned_ip = ''
  form.is_active = true
  form.remark = ''
  form.auto_assign_ip = true
  form.auto_create_proxy = true
}

onMounted(() => {
  store.fetchAccounts()
})

const handleCreate = () => {
  dialogType.value = 'create'
  resetForm()
  dialogVisible.value = true
}

const handleEdit = (account: Account) => {
  dialogType.value = 'edit'
  currentAccount.value = account
  form.username = account.username
  form.password = ''
  form.assigned_ip = account.assigned_ip
  form.is_active = account.is_active
  form.remark = account.remark
  form.auto_assign_ip = false
  dialogVisible.value = true
}

const handleSubmit = async () => {
  try {
    if (dialogType.value === 'create') {
      await store.createAccount(form)
      ElMessage.success('账号创建成功')
    } else if (currentAccount.value) {
      const data: Partial<AccountCreateDTO> = {
        username: form.username,
        assigned_ip: form.assigned_ip,
        is_active: form.is_active,
        remark: form.remark
      }
      if (form.password) {
        data.password = form.password
      }
      await store.updateAccount(currentAccount.value.id, data)
      ElMessage.success('账号更新成功')
    }
    dialogVisible.value = false
  } catch (e) {
    // 错误已在 request 拦截器中处理
  }
}

const handleDelete = async (account: Account) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除账号 "${account.username}" 吗？相关的代理配置也会被删除。`,
      '警告',
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }
    )
    await store.deleteAccount(account.id)
    ElMessage.success('账号已删除')
  } catch (e) {
    // 取消或错误
  }
}

const handleToggleActive = async (account: Account) => {
  try {
    const isActive = await store.toggleActive(account.id)
    ElMessage.success(isActive ? '账号已启用' : '账号已禁用')
  } catch (e) {
    // 错误已处理
  }
}

const handlePageChange = (page: number) => {
  store.currentPage = page
  store.fetchAccounts()
}
</script>

<template>
  <div class="accounts">
    <div class="page-header">
      <h2 class="page-header__title">账号管理</h2>
      <div class="page-header__actions">
        <el-button :icon="Refresh" @click="store.fetchAccounts()">刷新</el-button>
        <el-button type="primary" :icon="Plus" @click="handleCreate">新建账号</el-button>
      </div>
    </div>

    <div class="card">
      <el-table
        :data="store.accounts"
        v-loading="store.loading"
        stripe
      >
        <el-table-column prop="username" label="用户名" width="150" />
        <el-table-column prop="assigned_ip" label="分配 IP" width="130" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <span :class="['status-tag', row.is_online ? 'status-tag--online' : 'status-tag--offline']">
              {{ row.is_online ? '在线' : '离线' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="代理端口" width="100">
          <template #default="{ row }">
            {{ row.proxy_port || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="代理状态" width="100">
          <template #default="{ row }">
            <span v-if="row.proxy_port" :class="['status-tag', row.proxy_running ? 'status-tag--running' : 'status-tag--stopped']">
              {{ row.proxy_running ? '运行中' : '已停止' }}
            </span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="启用" width="80">
          <template #default="{ row }">
            <el-switch
              :model-value="row.is_active"
              @change="handleToggleActive(row)"
            />
          </template>
        </el-table-column>
        <el-table-column prop="remark" label="备注" show-overflow-tooltip />
        <el-table-column label="创建时间" width="170">
          <template #default="{ row }">
            {{ new Date(row.created_at).toLocaleString() }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <div class="table-actions">
              <el-button size="small" :icon="Edit" @click="handleEdit(row)">编辑</el-button>
              <el-button size="small" type="danger" :icon="Delete" @click="handleDelete(row)">删除</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="store.currentPage"
          :page-size="store.pageSize"
          :total="store.total"
          layout="total, prev, pager, next"
          @current-change="handlePageChange"
        />
      </div>
    </div>

    <!-- 新建/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogType === 'create' ? '新建账号' : '编辑账号'"
      width="500px"
    >
      <el-form :model="form" label-width="100px">
        <el-form-item label="用户名" required>
          <el-input v-model="form.username" placeholder="只能包含字母、数字和下划线" />
        </el-form-item>
        <el-form-item label="密码" :required="dialogType === 'create'">
          <el-input
            v-model="form.password"
            type="password"
            :placeholder="dialogType === 'edit' ? '留空则不修改' : '请输入密码'"
            show-password
          />
        </el-form-item>
        <el-form-item v-if="dialogType === 'create'" label="自动分配 IP">
          <el-switch v-model="form.auto_assign_ip" />
        </el-form-item>
        <el-form-item v-if="!form.auto_assign_ip || dialogType === 'edit'" label="IP 地址" required>
          <el-input v-model="form.assigned_ip" placeholder="10.0.0.x" />
        </el-form-item>
        <el-form-item v-if="dialogType === 'create'" label="创建代理">
          <el-switch v-model="form.auto_create_proxy" />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="form.is_active" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" :rows="2" placeholder="可选" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped lang="scss">
</style>
