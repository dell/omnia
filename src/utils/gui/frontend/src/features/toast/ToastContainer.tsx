import { useToastStore } from './toastStore'
import Toast from './Toast'

const ToastContainer = () => {
  const { toasts } = useToastStore()

  if (toasts.length === 0) return null

  return (
    <div className="toast-container">
      {toasts.map((toast) => (
        <Toast key={toast.id} toast={toast} />
      ))}
    </div>
  )
}

export default ToastContainer
