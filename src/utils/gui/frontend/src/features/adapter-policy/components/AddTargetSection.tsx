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

interface AddTargetSectionProps {
  newTargetName: string;
  onNameChange: (name: string) => void;
  onAdd: () => void;
  error: string;
}

export const AddTargetSection = ({ newTargetName, onNameChange, onAdd, error }: AddTargetSectionProps) => {
  return (
    <>
      <div className="flex mt-4">
        <input
          type="text"
          className="form-input flex-1"
          value={newTargetName}
          onChange={(e) => {
            onNameChange(e.target.value);
          }}
          placeholder="Enter target filename (e.g., service_k8s.json)"
        />
        <Button variant="primary" onClick={onAdd}>
          Add Target
        </Button>
      </div>
      {error && (
        <div className="error-message">{error}</div>
      )}
    </>
  );
};
