<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Document,
  Menu as IconMenu,
  Setting,
  User,
  Connection,
  DataLine
} from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const isCollapse = ref(false)

const menuItems = [
  { path: '/', title: '看板', icon: DataLine },
  { path: '/accounts', title: '账号管理', icon: User },
  { path: '/connections', title: '连接状态', icon: Connection },
  { path: '/proxies', title: '代理管理', icon: Setting },
  { path: '/logs', title: '系统日志', icon: Document }
]

const handleSelect = (path: string) => {
  router.push(path)
}
</script>

<template>
  <div class="layout">
    <aside class="layout__sidebar">
      <div class="logo">
        <span v-if="!isCollapse">L2TP Socks5</span>
        <span v-else>L2</span>
      </div>
      <el-menu
        :default-active="route.path"
        background-color="#304156"
        text-color="#bfcbd9"
        active-text-color="#409eff"
        :collapse="isCollapse"
        @select="handleSelect"
      >
        <el-menu-item
          v-for="item in menuItems"
          :key="item.path"
          :index="item.path"
        >
          <el-icon><component :is="item.icon" /></el-icon>
          <template #title>{{ item.title }}</template>
        </el-menu-item>
      </el-menu>
    </aside>

    <div class="layout__main">
      <header class="layout__header">
        <el-icon
          class="collapse-btn"
          @click="isCollapse = !isCollapse"
        >
          <IconMenu />
        </el-icon>
        <el-breadcrumb separator="/">
          <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
          <el-breadcrumb-item v-if="route.meta.title">
            {{ route.meta.title }}
          </el-breadcrumb-item>
        </el-breadcrumb>
      </header>

      <main class="layout__content">
        <RouterView />
      </main>
    </div>
  </div>
</template>

<style scoped lang="scss">
.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 18px;
  font-weight: 600;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.el-menu {
  border-right: none;
}

.collapse-btn {
  font-size: 20px;
  cursor: pointer;
  margin-right: 16px;

  &:hover {
    color: #409eff;
  }
}
</style>
