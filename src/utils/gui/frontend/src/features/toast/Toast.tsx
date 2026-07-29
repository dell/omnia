import { useEffect, useState } from 'react'
import { useToastStore, type ToastType } from './toastStore'

const Toast = ({ toast }: { toast: { id: string; message: string; type: ToastType } }) => {
  const { removeToast } = useToastStore()
  const [isVisible, setIsVisible] = useState(false)

  useEffect(() => {
    setIsVisible(true)
  }, [])

  const handleClose = () => {
    setIsVisible(false)
    setTimeout(() => removeToast(toast.id), 300)
  }

  const getIcon = () => {
    switch (toast.type) {
      case 'success':
        return '✓'
      case 'error':
        return '✕'
      case 'warning':
        return '⚠'
      case 'info':
      default:
        return 'ℹ'
    }
  }

  return (
    <div
      className={`toast toast-${toast.type} ${isVisible ? 'toast-visible' : ''}`}
      onClick={handleClose}
    >
      <span className="toast-icon">{getIcon()}</span>
      <span className="toast-message">{toast.message}</span>
      <button
        className="toast-close"
        onClick={(e) => {
          e.stopPropagation()
          handleClose()
        }}
        aria-label="Close"
      >
        ✕
      </button>
    </div>
  )
}

export default Toast
