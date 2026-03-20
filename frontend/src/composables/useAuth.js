import { storeToRefs } from 'pinia'
import { useAuthStore } from '@/stores/auth'

export const useAuth = () => {
  const store = useAuthStore()
  const { isAuthenticated, status, token, user } = storeToRefs(store)

  return {
    isAuthenticated,
    status,
    token,
    user,
    login: store.login,
    logout: store.logout,
    refreshSession: store.refreshSession,
    register: store.register,
  }
}
