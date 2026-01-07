import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
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
        },
        {
          path: 'connections',
          name: 'Connections',
          component: () => import('@/views/Connections.vue'),
          meta: { title: '连接状态' }
        },
        {
          path: 'proxies',
          name: 'Proxies',
          component: () => import('@/views/Proxies.vue'),
          meta: { title: '代理管理' }
        },
        {
          path: 'logs',
          name: 'Logs',
          component: () => import('@/views/Logs.vue'),
          meta: { title: '系统日志' }
        }
      ]
    }
  ]
})

router.beforeEach((to, _from, next) => {
  document.title = `${to.meta.title || 'L2TP Socks5'} - 代理管理系统`
  next()
})

export default router
