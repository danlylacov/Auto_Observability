type ConfirmOptions = {
  title?: string
  message: string
  details?: string
  confirmText?: string
  cancelText?: string
  type?: 'warning' | 'danger' | 'info'
}

type ConfirmResolver = (value: boolean) => void

let confirmResolver: ConfirmResolver | null = null

export const showConfirm = (options: ConfirmOptions): Promise<boolean> => {
  return new Promise((resolve) => {
    confirmResolver = resolve
    
    // Emit event to show dialog
    const event = new CustomEvent('show-confirm', { detail: options })
    window.dispatchEvent(event)
  })
}

export const resolveConfirm = (value: boolean) => {
  if (confirmResolver) {
    confirmResolver(value)
    confirmResolver = null
  }
}


