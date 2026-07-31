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
import { Link } from 'react-router-dom';

export const NotFound = () => {
  return (
    <div className="card notfound-card">
      <h2 className="notfound-title">Page Not Found</h2>
      <p className="notfound-text">
        The page you're looking for doesn't exist or has been moved.
      </p>
      <Link to="/" className="button button-primary">
        Go to Overview
      </Link>
    </div>
  );
};
