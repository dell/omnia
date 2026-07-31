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
import { DeploymentSetupStep } from './steps/deployment-setup/DeploymentSetupStep';
import { PxeFunctionalGroupsStep } from './steps/pxe/PxeFunctionalGroupsStep';
import { DeploymentConfigsStep as NetworkSpecStep } from './steps/network/DeploymentConfigsStep';
import { StorageConfigStep } from './steps/storage/StorageConfigStep';
import { CloudInitConfigStep } from './steps/cloud-init/CloudInitConfigStep';
import { OmniaHaDiscoveryStep } from './steps/omnia/OmniaHaDiscoveryStep';
import { TelemetryConfigStorageStep } from './steps/telemetry/TelemetryConfigStorageStep';
import { BuildStreamGitLabStep } from './steps/build-stream/BuildStreamGitLabStep';
import { SummaryAndGenerateStep } from './steps/summary/SummaryAndGenerateStep';

export const WIZARD_STEPS = [
  { id: 1, title: 'Deployment Setup', description: 'Select cluster type, configure optional features like Cloud-Init, BMC Discovery, Telemetry, Build Stream, and GitLab', component: DeploymentSetupStep },
  { id: 2, title: 'PXE Functional Groups', description: 'Configure PXE boot mapping, functional groups, DHCP settings, DNS, and kernel overrides for network booting', component: PxeFunctionalGroupsStep },
  { id: 3, title: 'Network Configuration', description: 'Configure admin and InfiniBand networks including subnets, IP addresses, DNS, NTP servers, and additional subnets', component: NetworkSpecStep },
  { id: 4, title: 'Storage Configuration', description: 'Configure storage mounts, mount profiles, PowerVault iSCSI, swap files, and S3 storage backend', component: StorageConfigStep },
  { id: 5, title: 'Cloud-Init Configuration', description: 'Configure additional cloud-init write_files and runcmd for common and per-functional-group node provisioning', component: CloudInitConfigStep },
  { id: 6, title: 'Omnia Cluster Configuration', description: 'Configure Slurm clusters, Kubernetes service clusters, high availability settings, and security configuration', component: OmniaHaDiscoveryStep },
  { id: 7, title: 'Telemetry Configuration', description: 'Configure telemetry sources (iDRAC, LDMS, DCGM, PowerScale, UFM, VAST, OME), bridges, and storage sinks (VictoriaMetrics, VictoriaLogs, Kafka)', component: TelemetryConfigStorageStep },
  { id: 8, title: 'Build Stream Configuration', description: 'Configure BuildStream host and GitLab integration for catalog management with project settings and resource limits', component: BuildStreamGitLabStep },
  { id: 9, title: 'Summary & Generate', description: 'Review all configuration settings and generate the deployment configuration files for download', component: SummaryAndGenerateStep },
] as const;
