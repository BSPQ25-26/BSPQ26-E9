import { waitForHealthyServices } from './helpers/backend.js'

export default async function globalSetup() {
  await waitForHealthyServices()
}
