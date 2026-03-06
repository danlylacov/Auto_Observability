export type ToastType = 'success' | 'error' | 'info' | 'warning'

export const showToast = (message: string, type: ToastType = 'info', duration: number = 5000) => {
  if (typeof window !== 'undefined' && (window as any).showToast) {
    ;(window as any).showToast(message, type, duration)
  } else {
    console.log(`[${type.toUpperCase()}] ${message}`)
  }
}

