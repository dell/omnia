// Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
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
