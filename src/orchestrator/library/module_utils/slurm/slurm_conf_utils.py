# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# These are the slurm options for version - 25.11
import re
import os
from enum import Enum
from collections import OrderedDict


class SlurmParserEnum(str, Enum):
    """Enumeration of Slurm configuration parameter types for parsing and validation."""

    S_P_IGNORE = "none"         # no value / ignored
    S_P_STRING = "str"          # generic string
    S_P_LONG = "int"            # integer (Python has only int)
    S_P_UINT16 = "int"          # unsigned int mapped to int
    S_P_UINT32 = "int"          # unsigned int mapped to int
    S_P_UINT64 = "int"          # unsigned int mapped to int
    S_P_POINTER = "object"      # generic object / pointer
    S_P_ARRAY = "array"         # list of dict
    S_P_BOOLEAN = "bool"        # boolean
    S_P_LINE = "str"            # line of text
    S_P_EXPLINE = "str"         # expanded line of text
    S_P_PLAIN_STRING = "str"    # plain string
    S_P_FLOAT = "float"         # floating point
    S_P_DOUBLE = "float"        # Python float is double precision
    S_P_LONG_DOUBLE = "float"   # approximate with float
    S_P_CSV = "csv"             # comma separated values
    S_P_LIST = "list"           # list of strings


# Convenience aliases (if other modules refer to S_P_* directly)
S_P_IGNORE = SlurmParserEnum.S_P_IGNORE
S_P_STRING = SlurmParserEnum.S_P_STRING
S_P_LONG = SlurmParserEnum.S_P_LONG
S_P_UINT16 = SlurmParserEnum.S_P_UINT16
S_P_UINT32 = SlurmParserEnum.S_P_UINT32
S_P_UINT64 = SlurmParserEnum.S_P_UINT64
S_P_POINTER = SlurmParserEnum.S_P_POINTER
S_P_ARRAY = SlurmParserEnum.S_P_ARRAY
S_P_BOOLEAN = SlurmParserEnum.S_P_BOOLEAN
S_P_LINE = SlurmParserEnum.S_P_LINE
S_P_EXPLINE = SlurmParserEnum.S_P_EXPLINE
S_P_PLAIN_STRING = SlurmParserEnum.S_P_PLAIN_STRING
S_P_FLOAT = SlurmParserEnum.S_P_FLOAT
S_P_DOUBLE = SlurmParserEnum.S_P_DOUBLE
S_P_LONG_DOUBLE = SlurmParserEnum.S_P_LONG_DOUBLE
S_P_CSV = SlurmParserEnum.S_P_CSV
S_P_LIST = SlurmParserEnum.S_P_LIST


slurm_downnodes_options = {
    "DownNodes": S_P_STRING,
    "Reason": S_P_STRING,
    "State": S_P_STRING,
}


slurm_nodename_options = {
    "NodeName": S_P_STRING,
    "BcastAddr": S_P_STRING,
    "Boards": S_P_UINT16,
    "CoreSpecCount": S_P_UINT16,
    "CoresPerSocket": S_P_UINT16,
    "CPUs": S_P_UINT16,
    "CPUSpecList": S_P_CSV,
    "CpuBind": S_P_STRING,
    "Feature": S_P_STRING,
    "Features": S_P_CSV,
    "Gres": S_P_CSV,
    "GresConf": S_P_STRING,
    "MemSpecLimit": S_P_UINT64,
    "NodeAddr": S_P_STRING,
    "NodeHostname": S_P_STRING,
    "Parameters": S_P_STRING,
    "Port": S_P_STRING,
    "Procs": S_P_UINT16,
    "RealMemory": S_P_UINT64,
    "Reason": S_P_STRING,
    "RestrictedCoresPerGPU": S_P_UINT16,
    "Sockets": S_P_UINT16,
    "SocketsPerBoard": S_P_UINT16,
    "State": S_P_STRING,
    "ThreadsPerCore": S_P_UINT16,
    "TmpDisk": S_P_UINT32,
    "Topology": S_P_CSV,
    "TRESWeights": S_P_STRING,
    "Weight": S_P_UINT32,
}


slurm_nodeset_options = {
    "NodeSet": S_P_STRING,
    "Feature": S_P_STRING,
    "Nodes": S_P_STRING
}


slurm_partitionname_options = {
    "PartitionName": S_P_STRING,
    "AllocNodes": S_P_CSV,
    "AllowAccounts": S_P_CSV,
    "AllowGroups": S_P_CSV,
    "AllowQos": S_P_CSV,
    "Alternate": S_P_STRING,
    "CpuBind": S_P_STRING,
    "DefCPUPerGPU": S_P_UINT64,
    "DefMemPerCPU": S_P_UINT64,
    "DefMemPerGPU": S_P_UINT64,
    "DefMemPerNode": S_P_UINT64,
    "Default": S_P_BOOLEAN,
    "DefaultTime": S_P_STRING,
    "DenyAccounts": S_P_CSV,
    "DenyQos": S_P_CSV,
    "DisableRootJobs": S_P_BOOLEAN,
    "ExclusiveUser": S_P_BOOLEAN,
    "ExclusiveTopo": S_P_BOOLEAN,
    "GraceTime": S_P_UINT32,
    "Hidden": S_P_BOOLEAN,
    "LLN": S_P_BOOLEAN,
    "MaxCPUsPerNode": S_P_UINT32,
    "MaxCPUsPerSocket": S_P_UINT32,
    "MaxMemPerCPU": S_P_UINT64,
    "MaxMemPerNode": S_P_UINT64,
    "MaxTime": S_P_STRING,
    "MaxNodes": S_P_UINT32,
    "MinNodes": S_P_UINT32,
    "Nodes": S_P_CSV,
    "OverSubscribe": S_P_STRING,
    "OverTimeLimit": S_P_STRING,
    "PowerDownOnIdle": S_P_BOOLEAN,
    "PreemptMode": S_P_STRING,
    "Priority": S_P_UINT16,
    "PriorityJobFactor": S_P_UINT16,
    "PriorityTier": S_P_UINT16,
    "QOS": S_P_STRING,
    "RootOnly": S_P_BOOLEAN,
    "ReqResv": S_P_BOOLEAN,
    "ResumeTimeout": S_P_UINT16,
    "SelectTypeParameters": S_P_STRING,
    "Shared": S_P_STRING,
    "State": S_P_STRING,
    "SuspendTime": S_P_STRING,
    "SuspendTimeout": S_P_UINT16,
    "Topology": S_P_STRING,
    "TRESBillingWeights": S_P_CSV
}

# From
# https://github.com/SchedMD/slurm/blob/slurm-<VERSION>/src/common/read_config.c
slurm_options = {
    "AccountingStorageBackupHost": S_P_STRING,
    "AccountingStorageEnforce": S_P_CSV,
    "AccountingStorageExternalHost": S_P_CSV,
    "AccountingStorageHost": S_P_STRING,
    "AccountingStorageParameters": S_P_CSV,
    "AccountingStoragePass": S_P_STRING,
    "AccountingStoragePort": S_P_UINT16,
    "AccountingStorageTRES": S_P_CSV,
    "AccountingStorageType": S_P_STRING,
    # {"AccountingStorageUser": S_P_STRING, _defunct_option,
    "AccountingStoreFlags": S_P_CSV,
    "AccountingStoreJobComment": S_P_BOOLEAN,
    "AcctGatherEnergyType": S_P_STRING,
    "AcctGatherFilesystemType": S_P_STRING,
    "AcctGatherInfinibandType": S_P_STRING,
    "AcctGatherInterconnectType": S_P_STRING,
    "AcctGatherNodeFreq": S_P_UINT16,
    "AcctGatherProfileType": S_P_STRING,
    "AllowSpecResourcesUsage": S_P_BOOLEAN,
    "AuthAltParameters": S_P_CSV,
    "AuthAltTypes": S_P_CSV,
    "AuthInfo": S_P_CSV,
    "AuthType": S_P_STRING,
    "BackupAddr": S_P_STRING,
    "BackupController": S_P_STRING,
    "BatchStartTimeout": S_P_UINT16,
    "BcastExclude": S_P_CSV,
    "BcastParameters": S_P_CSV,
    "BurstBufferParameters": S_P_STRING,
    "BurstBufferType": S_P_STRING,
    "CertgenType": S_P_STRING,
    "CertgenParameters": S_P_CSV,
    "CertmgrType": S_P_STRING,
    "CertmgrParameters": S_P_STRING,
    "CliFilterParameters": S_P_CSV,
    "CliFilterPlugins": S_P_CSV,
    "ClusterName": S_P_STRING,
    "CommunicationParameters": S_P_CSV,
    "CompleteWait": S_P_UINT16,
    "ControlAddr": S_P_STRING,
    "ControlMachine": S_P_STRING,
    # {"CoreSpecPlugin": S_P_STRING, _defunct_option,
    "CpuFreqDef": S_P_STRING,
    "CpuFreqGovernors": S_P_STRING,
    "CredType": S_P_STRING,
    "CryptoType": S_P_STRING,
    "DataParserParameters": S_P_STRING,
    "DebugFlags": S_P_CSV,
    "DefCPUPerGPU": S_P_UINT64,
    "DefMemPerCPU": S_P_UINT64,
    "DefMemPerGPU": S_P_UINT64,
    "DefMemPerNode": S_P_UINT64,
    "DependencyParameters": S_P_CSV,
    "DisableRootJobs": S_P_BOOLEAN,
    "EioTimeout": S_P_UINT16,
    "EnforcePartLimits": S_P_STRING,
    "Epilog": S_P_LIST,
    "EpilogMsgTime": S_P_UINT32,
    "EpilogSlurmctld": S_P_LIST,
    "EpilogTimeout": S_P_UINT16,
    # {"ExtSensorsFreq": S_P_UINT16, _defunct_option,
    # {"ExtSensorsType": S_P_STRING, _defunct_option,
    "FairShareDampeningFactor": S_P_UINT16,
    "FastSchedule": S_P_UINT16,
    "FederationParameters": S_P_CSV,
    "FirstJobId": S_P_UINT32,
    # {"GetEnvTimeout": S_P_UINT16, _defunct_option,
    "GpuFreqDef": S_P_STRING,
    "GresTypes": S_P_CSV,
    "GroupUpdateForce": S_P_UINT16,
    "GroupUpdateTime": S_P_UINT16,
    "HashPlugin": S_P_STRING,
    "HealthCheckInterval": S_P_UINT16,
    "HealthCheckNodeState": S_P_CSV,
    "HealthCheckProgram": S_P_STRING,
    "HttpParserType": S_P_STRING,
    "InactiveLimit": S_P_UINT16,
    "InteractiveStepOptions": S_P_STRING,
    "JobAcctGatherFrequency": S_P_STRING,
    "JobAcctGatherParams": S_P_STRING,
    "JobAcctGatherType": S_P_STRING,
    "JobCompHost": S_P_STRING,
    "JobCompLoc": S_P_STRING,
    "JobCompParams": S_P_CSV,
    "JobCompPass": S_P_STRING,
    "JobCompPassScript": S_P_STRING,
    "JobCompPort": S_P_UINT32,
    "JobCompType": S_P_STRING,
    "JobCompUser": S_P_STRING,
    "JobContainerType": S_P_STRING,
    # {"JobCredentialPrivateKey": S_P_STRING, _defunct_option,
    # {"JobCredentialPublicCertificate": S_P_STRING, _defunct_option,
    "JobFileAppend": S_P_UINT16,
    "JobRequeue": S_P_UINT16,
    "JobSubmitPlugins": S_P_CSV,
    "KeepAliveTime": S_P_UINT32,
    "KillOnBadExit": S_P_UINT16,
    "KillWait": S_P_UINT16,
    "LaunchParameters": S_P_STRING,
    "LaunchType": S_P_STRING,
    "Licenses": S_P_CSV,
    "LogTimeFormat": S_P_STRING,
    "MailDomain": S_P_STRING,
    "MailProg": S_P_STRING,
    "MaxArraySize": S_P_UINT32,
    "MaxBatchRequeue": S_P_UINT32,
    "MaxDBDMsgs": S_P_UINT32,
    "MaxJobCount": S_P_UINT32,
    "MaxJobId": S_P_UINT32,
    "MaxMemPerCPU": S_P_UINT64,
    "MaxMemPerNode": S_P_UINT64,
    "MaxNodeCount": S_P_UINT32,
    "MaxStepCount": S_P_UINT32,
    "MaxTasksPerNode": S_P_UINT16,
    "MCSParameters": S_P_STRING,
    "MCSPlugin": S_P_STRING,
    "MessageTimeout": S_P_UINT16,
    "MetricsType": S_P_STRING,
    "MinJobAge": S_P_UINT32,
    "MpiDefault": S_P_STRING,
    "MpiParams": S_P_CSV,
    "NamespaceType": S_P_STRING,
    "NodeFeaturesPlugins": S_P_STRING,
    "OverTimeLimit": S_P_UINT16,
    "PluginDir": S_P_STRING,
    "PlugStackConfig": S_P_STRING,
    # {"PowerParameters": S_P_STRING, _defunct_option,
    # {"PowerPlugin": S_P_STRING, _defunct_option,
    "PreemptExemptTime": S_P_STRING,
    "PreemptMode": S_P_CSV,
    "PreemptParameters": S_P_CSV,
    "PreemptType": S_P_STRING,
    "PrEpParameters": S_P_STRING,
    "PrEpPlugins": S_P_CSV,
    "PriorityCalcPeriod": S_P_STRING,
    "PriorityDecayHalfLife": S_P_STRING,
    "PriorityFavorSmall": S_P_BOOLEAN,
    "PriorityFlags": S_P_STRING,
    "PriorityMaxAge": S_P_STRING,
    "PriorityParameters": S_P_STRING,
    "PrioritySiteFactorParameters": S_P_STRING,
    "PrioritySiteFactorPlugin": S_P_STRING,
    "PriorityType": S_P_STRING,
    "PriorityUsageResetPeriod": S_P_STRING,
    "PriorityWeightAge": S_P_UINT32,
    "PriorityWeightAssoc": S_P_UINT32,
    "PriorityWeightFairshare": S_P_UINT32,
    "PriorityWeightJobSize": S_P_UINT32,
    "PriorityWeightPartition": S_P_UINT32,
    "PriorityWeightQOS": S_P_UINT32,
    "PriorityWeightTRES": S_P_CSV,
    "PrivateData": S_P_CSV,
    "ProctrackType": S_P_STRING,
    "Prolog": S_P_LIST,
    "PrologEpilogTimeout": S_P_UINT16,
    "PrologFlags": S_P_CSV,
    "PrologSlurmctld": S_P_LIST,
    "PrologTimeout": S_P_UINT16,
    "PropagatePrioProcess": S_P_UINT16,
    "PropagateResourceLimits": S_P_CSV,
    "PropagateResourceLimitsExcept": S_P_CSV,
    "RebootProgram": S_P_STRING,
    "ReconfigFlags": S_P_STRING,
    "RequeueExit": S_P_CSV,
    "RequeueExitHold": S_P_CSV,
    "ResumeFailProgram": S_P_STRING,
    "ResumeProgram": S_P_STRING,
    "ResumeRate": S_P_UINT16,
    "ResumeTimeout": S_P_UINT16,
    "ResvEpilog": S_P_STRING,
    "ResvOverRun": S_P_UINT16,
    "ResvProlog": S_P_STRING,
    "ReturnToService": S_P_UINT16,
    "RoutePlugin": S_P_STRING,
    "SallocDefaultCommand": S_P_STRING,
    "SbcastParameters": S_P_STRING,
    "SchedulerParameters": S_P_CSV,
    "SchedulerTimeSlice": S_P_UINT16,
    "SchedulerType": S_P_STRING,
    "ScronParameters": S_P_CSV,
    "SelectType": S_P_STRING,
    "SelectTypeParameters": S_P_STRING,
    "SlurmctldAddr": S_P_STRING,
    "SlurmctldDebug": S_P_STRING,
    "SlurmctldLogFile": S_P_STRING,
    "SlurmctldParameters": S_P_CSV,
    "SlurmctldPidFile": S_P_STRING,
    "SlurmctldPort": S_P_STRING,
    "SlurmctldPrimaryOffProg": S_P_STRING,
    "SlurmctldPrimaryOnProg": S_P_STRING,
    "SlurmctldSyslogDebug": S_P_STRING,
    "SlurmctldTimeout": S_P_UINT16,
    "SlurmdDebug": S_P_STRING,
    "SlurmdLogFile": S_P_STRING,
    "SlurmdParameters": S_P_CSV,
    "SlurmdPidFile": S_P_STRING,
    "SlurmdPort": S_P_UINT32,
    "SlurmdSpoolDir": S_P_STRING,
    "SlurmdSyslogDebug": S_P_STRING,
    "SlurmdTimeout": S_P_UINT16,
    "SlurmdUser": S_P_STRING,
    "SlurmSchedLogFile": S_P_STRING,
    "SlurmSchedLogLevel": S_P_UINT16,
    "SlurmUser": S_P_STRING,
    "SrunEpilog": S_P_STRING,
    "SrunPortRange": S_P_STRING,
    "SrunProlog": S_P_STRING,
    "StateSaveLocation": S_P_STRING,
    "SuspendExcNodes": S_P_CSV,
    "SuspendExcParts": S_P_CSV,
    "SuspendExcStates": S_P_STRING,
    "SuspendProgram": S_P_STRING,
    "SuspendRate": S_P_UINT16,
    "SuspendTime": S_P_STRING,
    "SuspendTimeout": S_P_UINT16,
    "SwitchParameters": S_P_CSV,
    "SwitchType": S_P_STRING,
    "TaskEpilog": S_P_STRING,
    "TaskPlugin": S_P_CSV,
    "TaskPluginParam": S_P_CSV,
    "TaskProlog": S_P_STRING,
    "TCPTimeout": S_P_UINT16,
    "TLSParameters": S_P_CSV,
    "TLSType": S_P_STRING,
    "TmpFS": S_P_STRING,
    "TopologyParam": S_P_CSV,
    "TopologyPlugin": S_P_STRING,
    "TrackWCKey": S_P_BOOLEAN,
    "TreeWidth": S_P_UINT16,
    "UnkillableStepProgram": S_P_STRING,
    "UnkillableStepTimeout": S_P_UINT16,
    "UrlParserType": S_P_STRING,
    "UsePAM": S_P_BOOLEAN,
    "VSizeFactor": S_P_UINT16,
    "WaitTime": S_P_UINT16,
    "X11Parameters": S_P_STRING,
    "DownNodes": S_P_ARRAY,
    "NodeName": S_P_ARRAY,
    "NodeSet": S_P_ARRAY,
    "PartitionName": S_P_ARRAY,
    "SlurmctldHost": S_P_LIST
}

# From
# https://github.com/SchedMD/slurm/blob/slurm-<VERSION>/src/slurmdbd/read_config.c
slurmdbd_options = {
    "AllowNoDefAcct": S_P_BOOLEAN,
    "AllResourcesAbsolute": S_P_BOOLEAN,
    "ArchiveDir": S_P_STRING,
    "ArchiveEvents": S_P_BOOLEAN,
    "ArchiveJobs": S_P_BOOLEAN,
    "ArchiveResvs": S_P_BOOLEAN,
    "ArchiveScript": S_P_STRING,
    "ArchiveSteps": S_P_BOOLEAN,
    "ArchiveSuspend": S_P_BOOLEAN,
    "ArchiveTXN": S_P_BOOLEAN,
    "ArchiveUsage": S_P_BOOLEAN,
    "AuthAltTypes": S_P_CSV,
    "AuthAltParameters": S_P_CSV,
    "AuthInfo": S_P_CSV,
    "AuthType": S_P_STRING,
    "CommitDelay": S_P_UINT16,
    "CommunicationParameters": S_P_CSV,
    "DbdAddr": S_P_STRING,
    "DbdBackupHost": S_P_STRING,
    "DbdHost": S_P_STRING,
    "DbdPort": S_P_UINT16,
    "DebugFlags": S_P_STRING,
    "DebugLevel": S_P_STRING,
    "DebugLevelSyslog": S_P_STRING,
    "DefaultQOS": S_P_STRING,
    "DisableCoordDBD": S_P_BOOLEAN,
    "DisableArchiveCommands": S_P_BOOLEAN,
    "HashPlugin": S_P_STRING,
    "JobPurge": S_P_UINT32,
    "LogFile": S_P_STRING,
    "LogTimeFormat": S_P_STRING,
    "MaxPurgeLimit": S_P_UINT32,
    "MaxQueryTimeRange": S_P_STRING,
    "MessageTimeout": S_P_UINT16,
    "Parameters": S_P_CSV,
    "PidFile": S_P_STRING,
    "PluginDir": S_P_STRING,
    "PrivateData": S_P_CSV,
    "PurgeEventAfter": S_P_STRING,
    "PurgeJobAfter": S_P_STRING,
    "PurgeResvAfter": S_P_STRING,
    "PurgeStepAfter": S_P_STRING,
    "PurgeSuspendAfter": S_P_STRING,
    "PurgeTXNAfter": S_P_STRING,
    "PurgeUsageAfter": S_P_STRING,
    "PurgeEventMonths": S_P_UINT32,
    "PurgeJobMonths": S_P_UINT32,
    "PurgeStepMonths": S_P_UINT32,
    "PurgeSuspendMonths": S_P_UINT32,
    "PurgeTXNMonths": S_P_UINT32,
    "PurgeUsageMonths": S_P_UINT32,
    "SlurmUser": S_P_STRING,
    "StepPurge": S_P_UINT32,
    "StorageBackupHost": S_P_STRING,
    "StorageHost": S_P_STRING,
    "StorageLoc": S_P_STRING,
    "StorageParameters": S_P_CSV,
    "StoragePass": S_P_STRING,
    "StoragePassScript": S_P_STRING,
    "StoragePort": S_P_UINT16,
    "StorageType": S_P_STRING,
    "StorageUser": S_P_STRING,
    "TCPTimeout": S_P_UINT16,
    "TLSParameters": S_P_CSV,
    "TLSType": S_P_STRING,
    "TrackWCKey": S_P_BOOLEAN,
    "TrackSlurmctldDown": S_P_BOOLEAN
}

# From
# https://github.com/SchedMD/slurm/blob/slurm-<VERSION>/src/interfaces/cgroup.c#L332
cgroup_options = {
    "CgroupAutomount": S_P_BOOLEAN,
    "CgroupMountpoint": S_P_STRING,
    "CgroupSlice": S_P_STRING,
    "ConstrainCores": S_P_BOOLEAN,
    "ConstrainRAMSpace": S_P_BOOLEAN,
    "AllowedRAMSpace": S_P_FLOAT,
    "MaxRAMPercent": S_P_FLOAT,
    "MinRAMSpace": S_P_UINT64,
    "ConstrainSwapSpace": S_P_BOOLEAN,
    "AllowedSwapSpace": S_P_FLOAT,
    "MaxSwapPercent": S_P_FLOAT,
    "MemoryLimitEnforcement": S_P_BOOLEAN,
    "MemoryLimitThreshold": S_P_FLOAT,
    "ConstrainDevices": S_P_BOOLEAN,
    "AllowedDevicesFile": S_P_STRING,
    "MemorySwappiness": S_P_UINT64,
    "CgroupPlugin": S_P_STRING,
    "IgnoreSystemd": S_P_BOOLEAN,
    "IgnoreSystemdOnFailure": S_P_BOOLEAN,
    "EnableControllers": S_P_BOOLEAN,
    "EnableExtraControllers": S_P_STRING,
    "SignalChildrenProcesses": S_P_BOOLEAN,
    "SystemdTimeout": S_P_UINT64
}

# From
# https://github.com/SchedMD/slurm/blob/slurm-<VERSION>s/src/interfaces/gres.c#L101C40-L116C2
_gres_options = {
    "AutoDetect": S_P_STRING,
    "Count": S_P_STRING,  # Number of Gres available
    "CPUs": S_P_STRING,  # CPUs to bind to Gres resource
    "Cores": S_P_CSV,  # Cores to bind to Gres resource
    "File": S_P_STRING,  # Path to Gres device
    "Files": S_P_STRING,  # Path to Gres device
    "Flags": S_P_STRING,  # GRES Flags
    "Link": S_P_STRING,  # Communication link IDs
    "Links": S_P_CSV,  # Communication link IDs
    "MultipleFiles": S_P_CSV,  # list of GRES device files
    "Type": S_P_STRING
}

gres_options = _gres_options.copy()
gres_options.update({
    "Name": S_P_ARRAY,
    "NodeName": S_P_ARRAY
})

gres_nodename_options = _gres_options.copy()
gres_nodename_options.update({
    "NodeName": S_P_STRING,
    "Name": S_P_STRING
})

gres_name_options = _gres_options.copy()
gres_name_options.update({
    "Name": S_P_STRING
})

# From
# https://github.com/SchedMD/slurm/blob/slurm-<VERSION>/src/plugins/mpi/pmix/mpi_pmix.c#L83
mpi_options = {
    "PMIxCliTmpDirBase": S_P_STRING,
    "PMIxCollFence": S_P_STRING,
    "PMIxDebug": S_P_UINT32,
    "PMIxDirectConn": S_P_BOOLEAN,
    "PMIxDirectConnEarly": S_P_BOOLEAN,
    "PMIxDirectConnUCX": S_P_BOOLEAN,
    "PMIxDirectSameArch": S_P_BOOLEAN,
    "PMIxEnv": S_P_STRING,
    "PMIxFenceBarrier": S_P_BOOLEAN,
    "PMIxNetDevicesUCX": S_P_STRING,
    "PMIxShareServerTopology": S_P_BOOLEAN,
    "PMIxTimeout": S_P_UINT32,
    "PMIxTlsUCX": S_P_CSV
}

# src/common/oci_config.c
oci_options = {
    "ContainerPath": S_P_STRING,
    "CreateEnvFile": S_P_STRING,
    "DisableHooks": S_P_STRING,
    "EnvExclude": S_P_STRING,
    "MountSpoolDir": S_P_STRING,
    "RunTimeCreate": S_P_STRING,
    "RunTimeDelete": S_P_STRING,
    "RunTimeKill": S_P_STRING,
    "RunTimeEnvExclude": S_P_STRING,
    "RunTimeQuery": S_P_STRING,
    "RunTimeRun": S_P_STRING,
    "RunTimeStart": S_P_STRING,
    "SrunPath": S_P_STRING,
    "SrunArgs": S_P_LIST,
    "DisableCleanup": S_P_BOOLEAN,
    "StdIODebug": S_P_STRING,
    "SyslogDebug": S_P_STRING,
    "FileDebug": S_P_STRING,
    "DebugFlags": S_P_STRING,
    "IgnoreFileConfigJson": S_P_BOOLEAN
}

# From
# src/plugins/acct_gather_*/*
acct_gather_options = {
    "EnergyIPMIDriverType": S_P_UINT32,
    "EnergyIPMIDisableAutoProbe": S_P_UINT32,
    "EnergyIPMIDriverAddress": S_P_UINT32,
    "EnergyIPMIRegisterSpacing": S_P_UINT32,
    "EnergyIPMIDriverDevice": S_P_STRING,
    "EnergyIPMIProtocolVersion": S_P_UINT32,
    "EnergyIPMIUsername": S_P_STRING,
    "EnergyIPMIPassword": S_P_STRING,
    "EnergyIPMIPrivilegeLevel": S_P_UINT32,
    "EnergyIPMIAuthenticationType": S_P_UINT32,
    "EnergyIPMICipherSuiteId": S_P_UINT32,
    "EnergyIPMISessionTimeout": S_P_UINT32,
    "EnergyIPMIRetransmissionTimeout": S_P_UINT32,
    "EnergyIPMIWorkaroundFlags": S_P_UINT32,
    "EnergyIPMIRereadSdrCache": S_P_BOOLEAN,
    "EnergyIPMIIgnoreNonInterpretableSensors": S_P_BOOLEAN,
    "EnergyIPMIBridgeSensors": S_P_BOOLEAN,
    "EnergyIPMIInterpretOemData": S_P_BOOLEAN,
    "EnergyIPMISharedSensors": S_P_BOOLEAN,
    "EnergyIPMIDiscreteReading": S_P_BOOLEAN,
    "EnergyIPMIIgnoreScanningDisabled": S_P_BOOLEAN,
    "EnergyIPMIAssumeBmcOwner": S_P_BOOLEAN,
    "EnergyIPMIEntitySensorNames": S_P_BOOLEAN,
    "EnergyIPMIFrequency": S_P_UINT32,
    "EnergyIPMICalcAdjustment": S_P_BOOLEAN,
    "EnergyIPMIPowerSensors": S_P_STRING,
    "EnergyIPMITimeout": S_P_UINT32,
    "EnergyIPMIVariable": S_P_STRING,
    "ProfileHDF5Dir": S_P_STRING,
    "ProfileHDF5Default": S_P_STRING,
    "ProfileInfluxDBDatabase": S_P_STRING,
    "ProfileInfluxDBDefault": S_P_STRING,
    "ProfileInfluxDBFrequency": S_P_UINT32,
    "ProfileInfluxDBHost": S_P_STRING,
    "ProfileInfluxDBPass": S_P_STRING,
    "ProfileInfluxDBRTPolicy": S_P_STRING,
    "ProfileInfluxDBTimeout": S_P_UINT32,
    "ProfileInfluxDBUser": S_P_STRING,
    "InterconnectOFEDPort": S_P_UINT32,
    "InfinibandOFEDPort": S_P_UINT32,
    "SysfsInterfaces": S_P_STRING
}

# src/plugins/burst_buffer/common/burst_buffer_common.c
burst_buffer_options = {
    "AllowUsers": S_P_STRING,
    "CreateBuffer": S_P_STRING,
    "DefaultPool": S_P_STRING,
    "DenyUsers": S_P_STRING,
    "DestroyBuffer": S_P_STRING,
    "Directive": S_P_STRING,
    "Flags": S_P_STRING,
    "GetSysState": S_P_STRING,
    "GetSysStatus": S_P_STRING,
    "Granularity": S_P_STRING,
    "OtherTimeout": S_P_UINT32,
    "PollInterval": S_P_UINT32,
    "Pools": S_P_STRING,
    "StageInTimeout": S_P_UINT32,
    "StageOutTimeout": S_P_UINT32,
    "StartStageIn": S_P_STRING,
    "StartStageOut": S_P_STRING,
    "StopStageIn": S_P_STRING,
    "StopStageOut": S_P_STRING,
    "ValidateTimeout": S_P_UINT32
}

# src/plugins/node_features/helpers/node_features_helpers.c
helpers_options = {
    "AllowUserBoot": S_P_STRING,
    "BootTime": S_P_UINT32,
    "ExecTime": S_P_UINT32,
    "Feature": S_P_ARRAY,
    "MutuallyExclusive": S_P_LIST,
    "NodeName": S_P_ARRAY
}

helpers_nodename_options = {
    "AllowUserBoot": S_P_STRING,
    "BootTime": S_P_UINT32,
    "ExecTime": S_P_UINT32,
    "Feature": S_P_CSV,
    "MutuallyExclusive": S_P_LIST
}

helpers_feature_options = {
    "Feature": S_P_CSV,
    "Helper": S_P_STRING,
    "Flags": S_P_STRING
}

# src/plugins/namespace/tmpfs/read_jcconf.c
job_container_options = {
    "AutoBasePath": S_P_BOOLEAN,
    "InitScript": S_P_STRING,
    "BasePath": S_P_ARRAY,
    "EntireStepInNS": S_P_BOOLEAN,
    "NodeName": S_P_ARRAY,
    "Shared": S_P_BOOLEAN,
    "CloneNSScript": S_P_STRING,
    "CloneNSEpilog": S_P_STRING,
    "CloneNSScript_Wait": S_P_UINT32,
    "CloneNSEpilog_Wait": S_P_UINT32
}

job_container_nodename_options = {
    "AutoBasePath": S_P_BOOLEAN,
    "BasePath": S_P_STRING,
    "Dirs": S_P_STRING,
    "EntireStepInNS": S_P_BOOLEAN,
    "NodeName": S_P_STRING,
    "Shared": S_P_BOOLEAN,
    "CloneNSScript": S_P_STRING,
    "CloneNSEpilog": S_P_STRING,
    "CloneNSScript_Wait": S_P_UINT32,
    "CloneNSEpilog_Wait": S_P_UINT32
}

job_container_basename_options = {
    "BasePath": S_P_STRING,
    "Dirs": S_P_STRING
}

# src/plugins/topology/tree/switch_record.c
topology_options = {
    "SwitchName": S_P_ARRAY,
    "LinkSpeed": S_P_UINT32,
    "Nodes": S_P_STRING,
    "Switches": S_P_STRING,
    "BlockName": S_P_ARRAY,
    "BlockSizes": S_P_STRING
}

topology_switchname_options = {
    "SwitchName": S_P_STRING,
    "LinkSpeed": S_P_UINT32,
    "Nodes": S_P_STRING,
    "Switches": S_P_STRING
}

topology_blockname_options = {
    "BlockName": S_P_STRING,
    "BlockSizes": S_P_STRING,
    "Nodes": S_P_STRING
}

all_confs = {
    "slurm": slurm_options,
    "slurmdbd": slurmdbd_options,
    "cgroup": cgroup_options,
    "mpi": mpi_options,
    "oci": oci_options,
    "acct_gather": acct_gather_options,
    "burst_buffer": burst_buffer_options,
    "helpers": helpers_options,
    "job_container": job_container_options,
    "topology": topology_options,
    "gres": gres_options,
    # TOD: GRES can have different combinations, NodeName and Name
    # https://slurm.schedmd.com/gres.conf.html#SECTION_EXAMPLES
    "slurm->PartitionName": slurm_partitionname_options,
    "slurm->NodeName": slurm_nodename_options,
    "slurm->DownNodes": slurm_downnodes_options,
    "slurm->NodeSet": slurm_nodeset_options,
    "gres->Name": gres_name_options,
    "gres->NodeName": gres_nodename_options,
    "job_container->NodeName": job_container_nodename_options,
    "job_container->BaseName": job_container_basename_options,
    "topology->SwitchName": topology_switchname_options,
    "topology->BlockName": topology_blockname_options,
    "helpers->NodeName": helpers_nodename_options,
    "helpers->Feature": helpers_feature_options
}

_HOSTLIST_RE = re.compile(
    r'^(?P<prefix>[^\[\]]*)\[(?P<inner>[^\[\]]+)\](?P<suffix>.*)$')


def validate_config_types(conf_dict, conf_name, module):
    """Validate configuration keys and value types based on SlurmParserEnum."""
    current_conf = all_confs.get(conf_name, {})
    if not current_conf:
        return {'invalid_keys': [], 'type_errors': []}
    invalid_keys = list(
        set(conf_dict.keys()).difference(set(current_conf.keys())))
    type_errors = []

    for key, value in conf_dict.items():
        if key in current_conf:
            expected_type_enum = current_conf[key]
            expected_type = expected_type_enum.value
            error = None

            if expected_type == "int":
                if not isinstance(value, int):
                    try:
                        int(str(value))
                    except (ValueError, TypeError):
                        error = f"Expected integer, got {type(value).__name__}"

            elif expected_type == "float":
                if not isinstance(value, (int, float)):
                    try:
                        float(str(value))
                    except (ValueError, TypeError):
                        error = f"Expected float, got {type(value).__name__}"

            elif expected_type == "bool":
                if not isinstance(value, bool):
                    if str(value).lower() not in [
                            'yes', 'no', 'true', 'false', '0', '1']:
                        error = f"Expected boolean, got {type(value).__name__}"

            elif expected_type == "str":
                if not isinstance(value, str):
                    error = f"Expected string, got {type(value).__name__}"

            elif expected_type == "csv":
                if not isinstance(value, str):
                    error = f"Expected CSV string, got {type(value).__name__}"

            elif expected_type == "list":
                if not isinstance(value, list):
                    error = f"Expected list, got {type(value).__name__}"

            elif expected_type == "array":
                if not isinstance(value, list):
                    error = f"Expected array (list), got {type(value).__name__}"
                elif value:
                    if not all(isinstance(item, dict) for item in value):
                        error = "Expected array of dicts, got mixed types"
                    else:
                        # Recursively validate each dict item in the array
                        for item in value:
                            item_result = validate_config_types(
                                item, f"{conf_name}->{key}", module)
                            type_errors.extend(item_result['type_errors'])
                            invalid_keys.extend(item_result['invalid_keys'])
            elif expected_type == "object":
                if not isinstance(value, (dict, object)):
                    error = f"Expected object, got {type(value).__name__}"

            if error:
                type_errors.append({  # format for error message in input validator
                    "error_key": "omnia_config.yml",
                    "error_msg": f"{conf_name}.conf: '{key}': {error} -> '{value}'",
                    "error_value": "slurm_cluster->config_sources"
                })
    return {
        'invalid_keys': list(invalid_keys),
        'type_errors': type_errors
    }


def parse_slurm_conf(file_path, conf_name, validate):
    """Parses the slurm.conf file and returns it as a dictionary."""
    current_conf = all_confs.get(conf_name, {})
    slurm_dict = OrderedDict()
    dup_keys = []

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"{file_path} not found.")

    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            # handles any comment after the data
            line = line.split('#')[0].strip()
            if not line:
                continue
            # Split the line by one or more spaces
            items = line.split()
            tmp_dict = OrderedDict()
            for item in items:
                # Split only on the first '=' to allow '=' inside the value
                key, value = item.split('=', 1)
                tmp_dict[key.strip()] = value.strip()
            skey = list(tmp_dict.keys())[0]
            if validate and skey not in current_conf:
                raise ValueError(
                    f"Invalid key while parsing {file_path}: {skey}")
            if current_conf.get(skey) == SlurmParserEnum.S_P_ARRAY or len(tmp_dict) > 1:
                slurm_dict[list(tmp_dict.keys())[0]] = list(
                    slurm_dict.get(list(tmp_dict.keys())[0], [])) + [tmp_dict]
            elif current_conf.get(skey) == SlurmParserEnum.S_P_CSV:
                existing_values = [
                    v.strip() for v in slurm_dict.get(
                        skey, "").split(',') if v.strip()]
                new_values = [v.strip()
                              for v in tmp_dict[skey].split(',') if v.strip()]
                slurm_dict[skey] = ",".join(
                    list(
                        dict.fromkeys(
                            existing_values +
                            new_values)))
            elif current_conf.get(skey) == SlurmParserEnum.S_P_LIST:
                slurm_dict[skey] = list(slurm_dict.get(
                    skey, [])) + list(tmp_dict.values())
            else:
                if skey in slurm_dict:
                    dup_keys.append(skey)
                else:
                    slurm_dict.update(tmp_dict)
    return slurm_dict, dup_keys


def expand_hostlist(expr):
    """
    Expand simple Slurm-style hostlist expressions, e.g.:
      dev[0-2,5,10-12] -> [dev0, dev1, dev2, dev5, dev10, dev11, dev12]
    If no brackets, returns [expr].
    """
    m = _HOSTLIST_RE.match(expr)
    if not m:
        return [expr]

    prefix = m.group("prefix")
    inner = m.group("inner")
    suffix = m.group("suffix")

    hosts = []
    for part in inner.split(','):
        part = part.strip()
        if '-' in part:
            start_s, end_s = part.split('-', 1)
            width = max(len(start_s), len(end_s))
            start = int(start_s)
            end = int(end_s)
            step = 1 if end >= start else -1
            for i in range(start, end + step, step):
                hosts.append(f"{prefix}{str(i).zfill(width)}{suffix}")
        else:
            # single index
            width = len(part)
            i = int(part)
            hosts.append(f"{prefix}{str(i).zfill(width)}{suffix}")
    return hosts
