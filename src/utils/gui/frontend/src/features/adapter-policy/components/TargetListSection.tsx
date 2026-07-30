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
import Button from '../../../components/Button';
import type { AdapterPolicyFormData } from '../schemas/adapterPolicy';

interface TargetListSectionProps {
  targets: AdapterPolicyFormData['targets'];
  onEditTarget: (targetName: string) => void;
  onRemoveTarget: (targetName: string) => void;
}

export const TargetListSection = ({ targets, onEditTarget, onRemoveTarget }: TargetListSectionProps) => {
  return (
    <div className="space-y-2 mb-4">
      {Object.keys(targets).map((targetName) => (
        <div key={targetName} className="border rounded p-4">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold">{targetName}</h3>
            <div className="flex items-center">
              <Button onClick={() => onEditTarget(targetName)}>
                Edit
              </Button>
              <Button onClick={() => onRemoveTarget(targetName)}>
                Remove
              </Button>
            </div>
          </div>
          <div className="text-sm text-gray-600">
            Sources: {targets[targetName].sources?.length || 0} | 
            Derived: {targets[targetName].derived?.length || 0}
          </div>
        </div>
      ))}
    </div>
  );
};
