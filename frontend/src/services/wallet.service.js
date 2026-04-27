import { transactionApiClient } from '@/services/api'

export const getWalletBalance = async () => {
  const { data } = await transactionApiClient.get('/wallet/balance')
  return data
}

export const topUpWallet = async (amount) => {
  const { data } = await transactionApiClient.post('/wallet/topup', {
    amount,
  })

  return data
}
