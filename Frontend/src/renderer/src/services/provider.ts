import { apiRequest } from './api'

export async function sendMessage(message: string) {
  return apiRequest('/chat', {
    method: 'POST',

    body: JSON.stringify({
      message
    })
  })
}
