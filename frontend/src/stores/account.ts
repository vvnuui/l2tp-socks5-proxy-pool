import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { accountApi } from '@/api/account'
import type { Account, AccountCreateDTO } from '@/types'

export const useAccountStore = defineStore('account', () => {
  const accounts = ref<Account[]>([])
  const loading = ref(false)
  const total = ref(0)
  const currentPage = ref(1)
  const pageSize = ref(20)

  const onlineAccounts = computed(() =>
    accounts.value.filter(a => a.is_online)
  )

  const fetchAccounts = async (params?: object) => {
    loading.value = true
    try {
      const res = await accountApi.getList({
        page: currentPage.value,
        page_size: pageSize.value,
        ...params
      })
      accounts.value = res.results
      total.value = res.count
    } finally {
      loading.value = false
    }
  }

  const createAccount = async (data: AccountCreateDTO) => {
    const account = await accountApi.create(data)
    accounts.value.unshift(account)
    total.value++
    return account
  }

  const updateAccount = async (id: number, data: Partial<AccountCreateDTO>) => {
    const account = await accountApi.update(id, data)
    const index = accounts.value.findIndex(a => a.id === id)
    if (index !== -1) {
      accounts.value[index] = account
    }
    return account
  }

  const deleteAccount = async (id: number) => {
    await accountApi.delete(id)
    accounts.value = accounts.value.filter(a => a.id !== id)
    total.value--
  }

  const toggleActive = async (id: number) => {
    const res = await accountApi.toggleActive(id)
    const index = accounts.value.findIndex(a => a.id === id)
    if (index !== -1) {
      accounts.value[index].is_active = res.is_active
    }
    return res.is_active
  }

  return {
    accounts,
    loading,
    total,
    currentPage,
    pageSize,
    onlineAccounts,
    fetchAccounts,
    createAccount,
    updateAccount,
    deleteAccount,
    toggleActive
  }
})
