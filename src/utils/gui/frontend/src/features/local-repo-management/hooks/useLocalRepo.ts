import { useMutation } from '@tanstack/react-query';
import { api, type JobStatus } from '../../../utils/api';

export const useGenerateLocalRepo = () => {
  return useMutation({
    mutationFn: (data: unknown) => api.localRepo.generate(data) as Promise<JobStatus>,
  });
};
