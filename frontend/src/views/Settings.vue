<script setup lang="ts">
import { onMounted, ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { serverConfigApi } from '@/api/proxy'
import { Refresh } from '@element-plus/icons-vue'
import type { ServerConfig } from '@/types'

const loading = ref(false)
const refreshing = ref(false)

const config = reactive<ServerConfig>({
  domain: '',
  public_ip: null,
  private_ip: null,
  server_address: '',
  updated_at: ''
})

const fetchConfig = async () => {
  loading.value = true
  try {
    const res = await serverConfigApi.get()
    Object.assign(config, res)
  } finally {
    loading.value = false
  }
}

const handleSave = async () => {
  loading.value = true
  try {
    const res = await serverConfigApi.update({ domain: config.domain })
    Object.assign(config, res)
    ElMessage.success('保存成功')
  } catch {
    // 错误已处理
  } finally {
    loading.value = false
  }
}

const handleRefreshIP = async () => {
  refreshing.value = true
  try {
    const res = await serverConfigApi.refreshIPs()
    Object.assign(config, res)
    ElMessage.success('IP 地址已更新')
  } catch {
    // 错误已处理
  } finally {
    refreshing.value = false
  }
}

onMounted(() => {
  fetchConfig()
})
</script>

<template>
  <div class="settings">
    <div class="page-header">
      <h2 class="page-header__title">系统设置</h2>
    </div>

    <div class="card" v-loading="loading">
      <div class="card__header">
        <span class="card__title">服务器地址配置</span>
      </div>

      <el-form label-width="120px" style="max-width: 600px">
        <el-form-item label="域名">
          <el-input
            v-model="config.domain"
            placeholder="例如: smx.szst.net"
            clearable
          />
          <div class="form-tip">配置域名后，代理连接地址将优先使用域名</div>
        </el-form-item>

        <el-form-item label="公网 IP">
          <el-input :model-value="config.public_ip || '未检测到'" disabled />
          <div class="form-tip">自动检测，无需手动设置</div>
        </el-form-item>

        <el-form-item label="内网 IP">
          <el-input :model-value="config.private_ip || '未检测到'" disabled />
          <div class="form-tip">自动检测，无需手动设置</div>
        </el-form-item>

        <el-form-item label="当前使用地址">
          <el-tag type="primary" size="large">{{ config.server_address }}</el-tag>
          <div class="form-tip">优先级：域名 > 公网 IP > 内网 IP</div>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="handleSave">保存域名</el-button>
          <el-button :icon="Refresh" :loading="refreshing" @click="handleRefreshIP">
            刷新 IP
          </el-button>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<style scoped lang="scss">
.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}
</style>
