import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ErrorBoundary from './components/ErrorBoundary';
import { NotFound } from './components/NotFound';
import Landing from './features/landing/Landing';
import PresetPicker from './features/preset-picker/PresetPicker';
import Overview from './features/overview/Overview';
import ConfigurationWizard from './features/configuration-wizard/ConfigurationWizard';
import { BmcDiscoveryFlow } from './features/configuration-wizard/BmcDiscoveryFlow';
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
            <Route path="/catalog" element={<CatalogViewer />} />
            <Route path="/catalog-editor" element={<CatalogEditor />} />
            <Route path="/local-repo" element={<Navigate to="/local-repo/rhel" replace />} />
            <Route path="/local-repo/:os" element={<LocalRepoManagement />} />
            <Route path="/adapter-policy" element={<AdapterPolicyEditor />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </Router>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}

export default App;
