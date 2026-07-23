import { z } from 'zod';
import { HOST_PORT_PATTERN, CERT_PATH_PATTERN, KEY_PATH_PATTERN } from './common';

// Shared schemas for repository entries
export const repoEntrySchema = z.object({
  url: z.string().url('Repository URL must be a valid URL'),
  name: z.string().min(1, 'Repository name is required').optional(),
  gpgkey: z.string().optional(),
  policy: z.union([z.enum(['always', 'partial'] as const, { message: 'Policy must be either "always" or "partial"' }), z.literal('')]).optional(),
  sslcacert: z.string().regex(CERT_PATH_PATTERN, 'SSL CA certificate must be a .crt file or empty').optional(),
  sslclientkey: z.string().regex(KEY_PATH_PATTERN, 'SSL client key must be a .key file or empty').optional(),
  sslclientcert: z.string().regex(CERT_PATH_PATTERN, 'SSL client certificate must be a .crt file or empty').optional(),
  caching: z.union([z.enum(['true', 'false'] as const, { message: 'Caching must be either "true" or "false"' }), z.literal('')]).optional(),
}).refine(
  (data) => {
    // gpgkey is optional, but if provided must be a valid URL
    if (data.gpgkey && data.gpgkey.trim() !== '') {
      try {
        new URL(data.gpgkey);
        return true;
      } catch {
        return false;
      }
    }
    return true;
  },
  {
    message: 'GPG key URL must be a valid URL when provided',
    path: ['gpgkey'],
  }
);

export const omniaRepoEntrySchema = z.object({
  url: z.string().url('Repository URL must be a valid URL'),
  name: z.string().min(1, 'Repository name is required').optional(),
  gpgkey: z.string().optional(),
  policy: z.union([z.enum(['always', 'partial'] as const, { message: 'Policy must be either "always" or "partial"' }), z.literal('')]).optional(),
  caching: z.union([z.enum(['true', 'false'] as const, { message: 'Caching must be either "true" or "false"' }), z.literal('')]).optional(),
}).refine(
  (data) => {
    // gpgkey is optional, but if provided must be a valid URL
    if (data.gpgkey && data.gpgkey.trim() !== '') {
      try {
        new URL(data.gpgkey);
        return true;
      } catch {
        return false;
      }
    }
    return true;
  },
  {
    message: 'GPG key URL must be a valid URL when provided',
    path: ['gpgkey'],
  }
);

// User registry entry schema with validation
export const userRegistryEntrySchema = z.object({
  host: z.string().regex(HOST_PORT_PATTERN, 'Registry host must be in format "IP:port" or "hostname:port"'),
  cert_path: z.string().regex(CERT_PATH_PATTERN, 'Certificate path must be a .crt file or empty'),
  key_path: z.string().regex(KEY_PATH_PATTERN, 'Key path must be a .key file or empty'),
}).refine(
  (data) => {
    // If host uses HTTPS, cert_path and key_path are required
    if (data.host && data.host.startsWith('https://')) {
      return !!data.cert_path && !!data.key_path;
    }
    return true;
  },
  {
    message: 'When using HTTPS, both certificate path and key path are required',
    path: ['cert_path'],
  }
).refine(
  (data) => {
    // If host uses HTTPS, cert_path and key_path are required
    if (data.host && data.host.startsWith('https://')) {
      return !!data.cert_path && !!data.key_path;
    }
    return true;
  },
  {
    message: 'When using HTTPS, both certificate path and key path are required',
    path: ['key_path'],
  }
);

export function getLocalRepoOsSchema(osType: 'rhel' | 'ubuntu') {
  return z.object({
    // User Registry Credential fields (array for field array usage)
    user_registry_credential: z.array(z.object({
      name: z.string().min(1, 'User registry name is required'),
      username: z.string().optional(),
      password: z.string().optional(),
    })).default([]),
    // Local Repo Config fields (array for field array usage)
    user_registry: z.array(userRegistryEntrySchema).optional(),
    user_repo_url_x86_64: z.array(repoEntrySchema).optional(),
    user_repo_url_aarch64: z.array(repoEntrySchema).optional(),
    additional_repos_x86_64: z.array(repoEntrySchema).optional(),
    additional_repos_aarch64: z.array(repoEntrySchema).optional(),
    // OS-specific repo keys
    [`${osType}_os_url_x86_64`]: z.array(repoEntrySchema).optional(),
    [`${osType}_os_url_aarch64`]: z.array(repoEntrySchema).optional(),
    [`omnia_repo_url_${osType}_x86_64`]: z.array(omniaRepoEntrySchema).optional(),
    [`omnia_repo_url_${osType}_aarch64`]: z.array(omniaRepoEntrySchema).optional(),
    [`${osType}_subscription_repo_config_x86_64`]: z.array(repoEntrySchema).optional(),
    [`${osType}_subscription_repo_config_aarch64`]: z.array(repoEntrySchema).optional(),
  });
}

// Convenience schemas for the existing wizard and new management page
export const localRepoUserRegistrySchema = getLocalRepoOsSchema('rhel');
export const localRepoUbuntuSchema = getLocalRepoOsSchema('ubuntu');

export type LocalRepoUserRegistryFormData = z.infer<typeof localRepoUserRegistrySchema>;
export type LocalRepoUbuntuFormData = z.infer<typeof localRepoUbuntuSchema>;
export type LocalRepoOsFormData = LocalRepoUserRegistryFormData | LocalRepoUbuntuFormData;
