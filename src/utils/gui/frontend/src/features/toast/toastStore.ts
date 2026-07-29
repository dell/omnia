import { create } from 'zustand'

export type ToastType = 'success' | 'error' | 'warning' | 'info'

export interface Toast {
  id: string
  message: string
  type: ToastType
  duration?: number
}

interface ToastState {
  toasts: Toast[]
  addToast: (message: string, type: ToastType, duration?: number) => void
  removeToast: (id: string) => void
  clearToasts: () => void
}

let toastCounter = 0
const toastTimers = new Map<string, NodeJS.Timeout>()

export const useToastStore = create<ToastState>((set) => ({
  toasts: [],
  addToast: (message, type, duration = 5000) => {
    const id = `${Date.now()}-${toastCounter++}`
    set((state) => ({
      toasts: [...state.toasts, { id, message, type, duration }]
    }))

    if (duration > 0) {
      const timer = setTimeout(() => {
        toastTimers.delete(id)
        set((state) => ({
          toasts: state.toasts.filter((toast) => toast.id !== id)
        }))
      }, duration)
      toastTimers.set(id, timer)
    }
  },
  removeToast: (id) => {
    const timer = toastTimers.get(id)
    if (timer) {
      clearTimeout(timer)
      toastTimers.delete(id)
    }
    set((state) => ({
      toasts: state.toasts.filter((toast) => toast.id !== id)
    }))
  },
  clearToasts: () => {
    toastTimers.forEach((timer) => clearTimeout(timer))
    toastTimers.clear()
    set({ toasts: [] })
  }
}))

// Helper function to show alerts
export const showAlert = (message: string, type: ToastType = 'info', duration?: number) => {
  useToastStore.getState().addToast(message, type, duration)
}
