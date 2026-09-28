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

#include <cuda_runtime.h>

#include <chrono>
#include <cstdio>

__global__ void touch_memory(float *data, size_t elements) {
    size_t index = blockIdx.x * blockDim.x + threadIdx.x;
    if (index < elements) {
        data[index] = data[index] + 1.0F;
    }
}

int main() {
    size_t free_memory = 0;
    size_t total_memory = 0;
    if (cudaMemGetInfo(&free_memory, &total_memory) != cudaSuccess) {
        return 1;
    }
    size_t allocation = free_memory / 4;
    float *device_data = nullptr;
    if (allocation == 0 || cudaMalloc(&device_data, allocation) != cudaSuccess) {
        return 2;
    }

    size_t elements = allocation / sizeof(float);
    auto started = std::chrono::steady_clock::now();
    unsigned long iterations = 0;
    while (std::chrono::duration_cast<std::chrono::seconds>(
               std::chrono::steady_clock::now() - started)
               .count() < 5) {
        touch_memory<<<(elements + 255) / 256, 256>>>(device_data, elements);
        if (cudaDeviceSynchronize() != cudaSuccess) {
            cudaFree(device_data);
            return 3;
        }
        ++iterations;
    }
    cudaFree(device_data);
    std::printf(
        "GPU_MEMORY_STRESS_OK bytes=%zu total=%zu iterations=%lu\n",
        allocation,
        total_memory,
        iterations
    );
    return iterations > 0 ? 0 : 4;
}
