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
