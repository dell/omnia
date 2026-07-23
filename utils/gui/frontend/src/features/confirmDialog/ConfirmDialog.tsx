import { useEffect } from 'react'
import { useConfirmDialogStore } from './confirmDialogStore'

const ConfirmDialog = () => {
  const isOpen = useConfirmDialogStore((s) => s.isOpen)
  const title = useConfirmDialogStore((s) => s.title)
  const message = useConfirmDialogStore((s) => s.message)
  const onConfirm = useConfirmDialogStore((s) => s.onConfirm)
  const onCancel = useConfirmDialogStore((s) => s.onCancel)
  const close = useConfirmDialogStore((s) => s.close)

  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = 'unset'
    }
    return () => {
      document.body.style.overflow = 'unset'
    }
  }, [isOpen])

  useEffect(() => {
    if (!isOpen) return
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') close()
    }
    document.addEventListener('keydown', handleEscape)
    return () => document.removeEventListener('keydown', handleEscape)
  }, [isOpen, close])

  if (!isOpen) return null

  return (
    <div className="confirm-dialog-overlay" onClick={close}>
      <div className="confirm-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="confirm-dialog-header">
          <h3>{title}</h3>
        </div>
        <div className="confirm-dialog-body">
          <p>{message}</p>
        </div>
        <div className="confirm-dialog-footer">
          <button
            className="button button-secondary"
            onClick={() => {
              onCancel()
              close()
            }}
          >
            Cancel
          </button>
          <button
            className="button button-primary"
            onClick={() => {
              onConfirm()
              close()
            }}
          >
            Confirm
          </button>
        </div>
      </div>
    </div>
  )
}

export default ConfirmDialog
