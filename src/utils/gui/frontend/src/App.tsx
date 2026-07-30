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
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ErrorBoundary from './components/ErrorBoundary';
import { NotFound } from './components/NotFound';
import Landing from './features/landing/Landing';
import PresetPicker from './features/preset-picker/PresetPicker';
import Overview from './features/overview/Overview';
import ConfigurationWizard from './features/configuration-wizard/ConfigurationWizard';
import { BmcDiscoveryFlow } from './features/configuration-wizard/BmcDiscoveryFlow';
import { MagellanDiscoveryFlow } from './features/configuration-wizard/MagellanDiscoveryFlow';
import CatalogViewer from './features/catalog/CatalogViewer';
import { AdapterPolicyEditor } from './features/adapter-policy/AdapterPolicyEditor';
import CatalogEditor from './features/catalog-editor/CatalogEditor';
import LocalRepoManagement from './features/local-repo-management/LocalRepoManagement';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  },
});

function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <Router>
          <Routes>
            <Route path="/" element={<Overview />} />
            <Route path="/landing" element={<Landing />} />
            <Route path="/preset-picker" element={<PresetPicker />} />
            <Route path="/wizard" element={<ConfigurationWizard />} />
            <Route path="/wizard/bmc-discovery" element={<BmcDiscoveryFlow />} />
            <Route path="/wizard/magellan-discovery" element={<MagellanDiscoveryFlow />} />
            <Route path="/catalog" element={<CatalogViewer />} />
            <Route path="/catalog-editor" element={<CatalogEditor />} />
            <Route path="/local-repo" element={<Navigate to="/local-repo/rhel" replace />} />
            <Route path="/local-repo/rhel" element={<LocalRepoManagement />} />
            {/* <Route path="/local-repo/:os" element={<LocalRepoManagement />} /> */}
            <Route path="/adapter-policy" element={<AdapterPolicyEditor />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </Router>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}

export default App;
