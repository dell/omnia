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
