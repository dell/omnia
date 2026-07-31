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

export type LocalRepoOsType = 'rhel' | 'ubuntu';

export interface LocalRepoOsData {
  user_registry_credential?: any[];
  user_registry?: any[];
  user_repo_url_x86_64?: any[];
  user_repo_url_aarch64?: any[];
  additional_repos_x86_64?: any[];
  additional_repos_aarch64?: any[];
  [key: string]: any;
}

interface LocalRepoState {
  activeOs: LocalRepoOsType;
  rhel: LocalRepoOsData;
  ubuntu: LocalRepoOsData;
  setActiveOs: (os: LocalRepoOsType) => void;
  setOsData: (os: LocalRepoOsType, data: Partial<LocalRepoOsData>) => void;
  resetOs: (os: LocalRepoOsType) => void;
}

const emptyOsData = (): LocalRepoOsData => ({
  user_registry_credential: [],
  user_registry: [],
  user_repo_url_x86_64: [],
  user_repo_url_aarch64: [],
  additional_repos_x86_64: [],
  additional_repos_aarch64: [],
  _ui_activeTab: 'credentials',
  _ui_showCredentials: false,
  _ui_showUserRegistry: false,
  _ui_showUserRepos: false,
  _ui_showAdditionalRepos: false,
  _ui_showRhelRepos: false,
  _ui_showRhelSubscription: false,
  _ui_showUbuntuRepos: false,
  _ui_showUbuntuSubscription: false,
});

export const useLocalRepoStore = create<LocalRepoState>()(
  persist(
    (set) => ({
      activeOs: 'rhel',
      rhel: emptyOsData(),
      ubuntu: emptyOsData(),
      setActiveOs: (activeOs) => set({ activeOs }),
      setOsData: (os, data) =>
        set((state) => ({
          [os]: { ...state[os], ...data },
        } as Partial<LocalRepoState>)),
      resetOs: (os) =>
        set({
          [os]: emptyOsData(),
        } as Partial<LocalRepoState>),
    }),
    {
      name: 'omnia-local-repo-management-storage',
      version: 1,
      partialize: (state) => ({
        activeOs: state.activeOs,
        rhel: state.rhel,
        ubuntu: state.ubuntu,
      }),
    }
  )
);
