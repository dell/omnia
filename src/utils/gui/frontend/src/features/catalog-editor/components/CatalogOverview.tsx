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
import { useCatalogStore } from '../catalogStore';

const CatalogOverview = () => {
  const catalogRoot = useCatalogStore((s) => s.catalogRoot);
  const setCatalogRoot = useCatalogStore((s) => s.setCatalogRoot);

  if (!catalogRoot) return <p>No catalog loaded</p>;

  const inner = catalogRoot.Catalog;

  const updateMetadata = (
    field: 'Name' | 'Version' | 'Identifier',
    value: string,
  ) => {
    setCatalogRoot({
      ...catalogRoot,
      Catalog: { ...inner, [field]: value },
    });
  };

  return (
    <div className="p-8">
      <h2>Catalog Overview</h2>

      <div className="mb-4">
        <h3>Metadata</h3>
        <div className="grid-2-col">
          <div className="form-group">
            <label className="form-label">Name:</label>
            <input
              type="text"
              value={inner.Name}
              onChange={(e) =>
                updateMetadata('Name', e.target.value)
              }
              className="form-input"
            />
          </div>
          <div className="form-group">
            <label className="form-label">Version:</label>
            <input
              type="text"
              value={inner.Version}
              onChange={(e) =>
                updateMetadata('Version', e.target.value)
              }
              className="form-input"
            />
          </div>
          <div className="form-group">
            <label className="form-label">Identifier:</label>
            <input
              type="text"
              value={inner.Identifier}
              onChange={(e) =>
                updateMetadata('Identifier', e.target.value)
              }
              className="form-input"
            />
          </div>
        </div>
      </div>

      <div className="mb-4">
        <h3>Statistics</h3>
        <div className="grid-2-col">
          <div className="text-small-muted">
            Functional Layers:{' '}
            {inner.FunctionalLayer.length}
          </div>
          <div className="text-small-muted">
            Functional Packages:{' '}
            {Object.keys(inner.FunctionalPackages).length}
          </div>
          <div className="text-small-muted">
            OS Packages:{' '}
            {Object.keys(inner.OSPackages).length}
          </div>
          <div className="text-small-muted">
            Infrastructure Packages:{' '}
            {
              Object.keys(inner.InfrastructurePackages)
                .length
            }
          </div>
        </div>
      </div>
    </div>
  );
};

export default CatalogOverview;
