import { create } from 'zustand'

interface ConfirmDialogState {
  isOpen: boolean
  title: string
  message: string
  onConfirm: () => void
  onCancel: () => void
  showConfirm: (title: string, message: string, onConfirm: () => void, onCancel?: () => void) => void
  close: () => void
}

export const useConfirmDialogStore = create<ConfirmDialogState>((set) => ({
  isOpen: false,
  title: '',
  message: '',
  onConfirm: () => {},
  onCancel: () => {},
  showConfirm: (title, message, onConfirm, onCancel) =>
    set({
      isOpen: true,
      title,
      message,
      onConfirm,
      onCancel: onCancel || (() => set({ isOpen: false }))
    }),
  close: () => set({
    isOpen: false,
    title: '',
    message: '',
    onConfirm: () => {},
    onCancel: () => {}
  })
}))

// Helper function to show confirmation dialog
export const showConfirm = (
  title: string,
  message: string,
  onConfirm: () => void,
  onCancel?: () => void
) => {
  useConfirmDialogStore.getState().showConfirm(title, message, onConfirm, onCancel)
}
