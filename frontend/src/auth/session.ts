import { computed, ref } from 'vue'
import axios from 'axios'

const TOKEN_KEY = 'access_token'

const API_BASE = import.meta.env.VITE_API_URL || ''

export const accessToken = ref<string | null>(localStorage.getItem(TOKEN_KEY))
export const username = ref('')
export const role = ref('')

export const isAuthenticated = computed(() => Boolean(accessToken.value))
export const isMaintainer = computed(() => role.value === 'maintainer')

export function clearSession(): void {
  localStorage.removeItem(TOKEN_KEY)
  accessToken.value = null
  username.value = ''
  role.value = ''
}

export function setSession(token: string, uname: string, r: string): void {
  localStorage.setItem(TOKEN_KEY, token)
  accessToken.value = token
  username.value = uname
  role.value = r
}

export async function restoreSession(): Promise<void> {
  const t = localStorage.getItem(TOKEN_KEY)
  if (!t) {
    clearSession()
    return
  }
  accessToken.value = t
  try {
    const { data } = await axios.get<{ username: string; role: string }>(
      `${API_BASE}/api/v1/auth/me`,
      { headers: { Authorization: `Bearer ${t}` } }
    )
    username.value = data.username
    role.value = data.role
  } catch {
    clearSession()
  }
}
