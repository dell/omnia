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
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { CatalogRoot } from './schemas/catalogSchema';

type ActiveSection =
  | 'overview'
  | 'layers'
  | 'os'
  | 'infrastructure'
  | 'driver-packages'
  | 'miscellaneous'
  | 'validation';

interface CatalogState {
  // Data
  catalogRoot: CatalogRoot | null;
  setCatalogRoot: (root: CatalogRoot) => void;

  // UI
  activeSection: ActiveSection;
  setActiveSection: (section: ActiveSection) => void;

  // Validation
  validationErrors: string[];
  validationWarnings: string[];
  setValidationResults: (
    errors: string[],
    warnings: string[],
  ) => void;
}

export const useCatalogStore = create<CatalogState>()(
  persist(
    (set) => ({
      catalogRoot: null,
      setCatalogRoot: (root) => set({ catalogRoot: root }),

      activeSection: 'overview',
      setActiveSection: (section) =>
        set({ activeSection: section }),

      validationErrors: [],
      validationWarnings: [],
      setValidationResults: (errors, warnings) =>
        set({
          validationErrors: errors,
          validationWarnings: warnings,
        }),
    }),
    {
      name: 'catalog-editor-storage',
      // Persist catalog data and navigation state to survive page refreshes
      partialize: (state) => ({
        catalogRoot: state.catalogRoot,
        activeSection: state.activeSection,
      }),
    },
  ),
);
