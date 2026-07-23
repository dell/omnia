import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api'

export const useGenerateAll = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: api.config.generateAll,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['job-status'] })
    },
  })
}

export const useJobStatus = (jobId: string) => {
  return useQuery({
    queryKey: ['job-status', jobId],
    queryFn: () => api.config.getJobStatus(jobId),
    enabled: !!jobId,
    refetchInterval: (query: any) => {
      const data = query.state.data
      // Standard React Query pattern: poll while in progress, stop when complete or failed
      if (data?.status === 'in_progress') return 50  // Very fast polling for quick jobs
      // Keep polling briefly if completed but no result yet (race condition protection)
      if (data?.status === 'completed' && !data?.result) return 50
      if (data?.status === 'failed' && !data?.error) return 50
      return false
    },
  })
}

