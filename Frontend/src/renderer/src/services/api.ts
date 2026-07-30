const BASE_URL = 'http://127.0.0.1:8000'

export async function apiRequest(endpoint: string, options: RequestInit = {}) {
  const response = await fetch(BASE_URL + endpoint, {
    headers: {
      'Content-Type': 'application/json'
    },
    ...options
  })

  if (!response.ok) {
    throw new Error(await response.text())
  }

  return response.json()
}
