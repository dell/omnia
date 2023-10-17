# Copyright 2023 Dell Inc. or its subsidiaries. All Rights Reserved.
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

'''
Module to gather gpu related metrics
'''
import math
import data_collector_nvidia_gpu
import data_collector_amd_gpu
import utility
import prerequisite

class GPUMetricCollector:
    '''
    GPUMetricCollector class is responsible for collecting all gpu metrics
    '''

    def __init__(self):
        self.gpu_metric_output_dict = {}
        self.gpu_unit = {}

    def get_nvidia_metrics(self):
        '''
        This method collects all the nvidia gpu metrics
        '''
        # run nvidia-smi command and store output in a variable
        nvidia_metrics_cmd_output = data_collector_nvidia_gpu.get_nvidia_metrics_output()

        # get temperature details for NVIDIA GPU
        gpu_temp = data_collector_nvidia_gpu.get_nvidia_gpu_temp(nvidia_metrics_cmd_output)
        if gpu_temp is not None:
            for index, item in enumerate(gpu_temp):
                self.gpu_metric_output_dict["gpu_temperature:gpu" + str(index)] = str(item)
                self.gpu_unit["gpu_temperature"] = "C"
        else:
            self.gpu_metric_output_dict["gpu_temperature:gpu"] = utility.Result.NO_DATA.value

        # get utilization details for NVIDIA GPU
        gpu_util = data_collector_nvidia_gpu.get_nvidia_gpu_utilization(nvidia_metrics_cmd_output)
        if gpu_util is not None:
            for index, item in enumerate(gpu_util):
                self.gpu_metric_output_dict["gpu_utilization:gpu" + str(index)] = str(item)
                self.gpu_unit["gpu_utilization"] = "percent"
        else:
            self.gpu_metric_output_dict["gpu_utilization:gpu"] = utility.Result.NO_DATA.value

        # get average of utilization of all GPUs in the system
        gpu_avg_util = data_collector_nvidia_gpu.get_nvidia_gpu_avg_utilization(nvidia_metrics_cmd_output)
        if gpu_avg_util is not None:
            self.gpu_metric_output_dict["gpu_utilization:average"] = str(gpu_avg_util)
            self.gpu_unit["gpu_utilization"] = "percent"
        else:
            self.gpu_metric_output_dict["gpu_utilization:average"] = utility.Result.NO_DATA.value

    def get_amd_metrics(self):
        '''
        This method collects all the AMD gpu metrics
        '''
        # get temperature details for AMD GPU
        gpu_temp = data_collector_amd_gpu.get_amd_gpu_temp()
        if gpu_temp is not None:
            for keys, values in gpu_temp.items():
                for index, value in enumerate(values):
                    if not math.isnan(float(value)):
                        self.gpu_metric_output_dict['gpu_temperature:' + keys + ':gpu' + str(index)] = str(value)
                        self.gpu_unit['gpu_temperature:' + keys] = "C"
                    else:
                        self.gpu_metric_output_dict[
                            'gpu_temperature:' + keys + ':gpu' + str(index)] = utility.Result.NO_DATA.value
        else:
            self.gpu_metric_output_dict["gpu_temperature:gpu"] = utility.Result.NO_DATA.value

        # get utilization details for AMD GPU
        gpu_util = data_collector_amd_gpu.get_amd_gpu_utilization()
        if gpu_util is not None:
            for index, item in enumerate(gpu_util):
                self.gpu_metric_output_dict["gpu_utilization:gpu" + str(index)] = str(item)
                self.gpu_unit["gpu_utilization:gpu"] = "percent"
        else:
            self.gpu_metric_output_dict["gpu_utilization:gpu"] = utility.Result.NO_DATA.value

        # get average of utilization of all GPUs in the system
        gpu_avg_util = data_collector_amd_gpu.get_amd_gpu_avg_utilization(gpu_util)
        if gpu_avg_util is not None:
            self.gpu_metric_output_dict["gpu_utilization:average"] = str(gpu_avg_util)
            self.gpu_unit["gpu_utilization:average"] = "percent"
        else:
            self.gpu_metric_output_dict["gpu_utilization:average"] = utility.Result.NO_DATA.value

    def metric_collector(self, aggregation_level):
        '''
        This method collects all the gpu metric parameters.
        '''
        # Run only when nvidia gpu present
        if prerequisite.dict_component_existence['nvidiagpu']:
            self.get_nvidia_metrics()
        # Run only when amd gpu present
        if prerequisite.dict_component_existence['amdgpu']:
            self.get_amd_metrics()

        if prerequisite.dict_component_existence['nvidiagpu'] is False and prerequisite.dict_component_existence[
            'amdgpu'] is False:
            self.gpu_metric_output_dict["gpu_temperature"] = utility.Result.NO_DATA.value
            self.gpu_metric_output_dict["gpu_utilization"] = utility.Result.NO_DATA.value
            self.gpu_metric_output_dict["gpu_utilization:average"] = utility.Result.NO_DATA.value