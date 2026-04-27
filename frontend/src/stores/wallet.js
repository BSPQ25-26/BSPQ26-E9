import { defineStore } from 'pinia'
import { getWalletBalance, topUpWallet } from '@/services/wallet.service'

const normalizeBalancePayload = (payload) => ({
  balance: Number(payload?.balance) || 0,
  lastUpdate: payload?.last_update || null,
  userId: payload?.user_id || '',
})

export const useWalletStore = defineStore('wallet', {
  state: () => ({
    balance: 0,
    error: '',
    lastUpdate: null,
    status: 'idle',
    topUpStatus: 'idle',
    userId: '',
  }),
  getters: {
    isLoading: (state) => state.status === 'loading',
    isTopUpLoading: (state) => state.topUpStatus === 'loading',
  },
  actions: {
    applyBalance(payload) {
      const normalizedPayload = normalizeBalancePayload(payload)

      this.balance = normalizedPayload.balance
      this.lastUpdate = normalizedPayload.lastUpdate
      this.userId = normalizedPayload.userId
    },
    reset() {
      this.balance = 0
      this.error = ''
      this.lastUpdate = null
      this.status = 'idle'
      this.topUpStatus = 'idle'
      this.userId = ''
    },
    async fetchBalance() {
      this.status = 'loading'
      this.error = ''

      try {
        const data = await getWalletBalance()
        this.applyBalance(data)
        return data
      } catch (error) {
        this.error =
          error?.response?.data?.detail || 'We could not load your wallet balance.'
        throw error
      } finally {
        this.status = 'idle'
      }
    },
    async topUp(amount) {
      this.topUpStatus = 'loading'
      this.error = ''

      try {
        const data = await topUpWallet(amount)
        this.applyBalance(data)
        return data
      } catch (error) {
        this.error = error?.response?.data?.detail || 'We could not top up your wallet.'
        throw error
      } finally {
        this.topUpStatus = 'idle'
      }
    },
  },
})
