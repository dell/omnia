# Omnia GUI Module

Web-based interface for Omnia configuration management, providing comprehensive tools for catalog editing, configuration wizard, and adapter policy transformations.

## Overview

The GUI Module provides a modern web-based interface for managing Omnia configurations. It consists of three main sub-modules:

- **Catalog Editor GUI**: Visual editor for Omnia catalog JSON files with real-time validation
- **Configuration Wizard**: Step-by-step wizard for deployment configuration with conditional per-step tabs
- **Adapter Policy Module**: Interface for adapter policy transformations

## Architecture

The GUI Module follows a modern web architecture with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────┐
│                     Frontend (React)                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │ Catalog      │  │ Configuration│  │ Adapter      │   │
│  │ Editor       │  │ Wizard       │  │ Policy       │   │
│  └──────────────┘  └──────────────┘  └──────────────┘   │
│  ┌──────────────────────────────────────────────────┐   │
│  │       Zustand State Management + TanStack Query  │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                  Backend (FastAPI)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │ Catalog      │  │ Configuration│  │ Adapter      │   │
│  │ Service      │  │ Service      │  │ Service      │   │
│  └──────────────┘  └──────────────┘  └──────────────┘   │
│  ┌──────────────────────────────────────────────────┐   │
│  │         In-Memory Catalog + Job Store            │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

## Directory Structure

```
gui/
├── backend/         # Backend FastAPI application
│   ├── app.py                   # FastAPI application entry point
│   ├── api/v1/                  # API endpoints
│   │   ├── routes/              # Route handlers
│   │   │   ├── catalog_routes.py
│   │   │   ├── catalog_editor_routes.py
│   │   │   ├── wizard_routes.py
│   │   │   ├── local_repo_routes.py
│   │   │   └── adapter_policy_routes.py
│   │   ├── schemas/             # Pydantic schemas
│   │   └── dependencies.py      # Dependency injection / service providers
│   ├── config/                  # Settings and logging
│   ├── core/                    # Middleware and exception handling
│   ├── models/                  # Data models
│   ├── services/                # Business logic
│   └── utils/                   # Utilities
├── frontend/                    # Frontend React + Vite application
│   ├── src/
│   │   ├── features/            # Feature-based modules
│   │   │   ├── catalog-editor/
│   │   │   ├── catalog/
│   │   │   ├── configuration-wizard/
│   │   │   ├── adapter-policy/
│   │   │   ├── local-repo-management/
│   │   │   ├── preset-picker/
│   │   │   ├── landing/
│   │   │   ├── overview/
│   │   │   ├── toast/
│   │   │   └── confirmDialog/
│   │   ├── components/          # Shared components
│   │   └── hooks/               # Shared hooks
│   ├── package.json
│   └── vite.config.ts
└── out/                         # Generated output files directory
```

## Features

### Catalog Editor GUI

- **Visual Catalog Management**: Web-based CRUD for catalog packages and layers
- **Real-time Validation**: Immediate feedback with L1/L2 validation
- **In-Memory Editing**: Edit catalog in memory, save on demand
- **Preset Picker**: Load catalog templates from repository
- **Auto-Populate**: Automatically populate functional layers from roles
- **State Persistence**: Maintain edits across page refreshes
- **Bundle Selector**: Select packages from predefined bundles
- **Import/Export**: Load and save catalog JSON files

### Configuration Wizard

- **Step-by-Step Configuration**: 9 main steps for comprehensive configuration
- **Conditional Tabs**: Per-step tabs for detailed configuration (e.g., 9 telemetry source/sink tabs)
- **PXE Mapping**: PXE mapping file upload and editing
- **Config File Generation**: Automatic generation of YAML configuration files
- **State Persistence**: Maintain wizard data across navigation
- **Job Queue**: Async operation management with job tracking

### Adapter Policy Module

- **Policy Transformation**: Transform catalog data to adapter policy format
- **Field Mapping**: Map catalog fields to adapter policy fields
- **Filtering**: Filter packages by allowlist or functional layers
- **Deduplication**: Remove duplicate packages
- **Validation**: Validate adapter policy configuration

## Backend Setup

### Prerequisites

- Python 3.12+
- FastAPI
- Pydantic
- Python dependencies listed in `backend/requirements.txt`

### Installation

```bash
cd utils/gui
pip install -r backend/requirements.txt
```

Dependencies are in `utils/gui/backend/requirements.txt`.

### Configuration

Configuration is managed through environment variables and settings in `backend/config/settings.py`. Key environment variables include:

- `API_TITLE`: API title
- `API_DESCRIPTION`: API description
- `API_VERSION`: API version
- `API_PREFIX`: API endpoint prefix (default: `/api/v1`)
- `HOST`: Server host (default: `0.0.0.0`)
- `PORT`: Server port (default: `8000`)
- `RELOAD`: Auto-reload in development (default: `true`)
- `LOG_LEVEL`: Logging level (default: `info`)
- `CORS_ORIGINS`: Comma-separated allowed CORS origins
- `CORS_ALLOW_CREDENTIALS`: Allow credentials (default: `true`)
- `CORS_ALLOW_METHODS`: Allowed HTTP methods
- `CORS_ALLOW_HEADERS`: Allowed HTTP headers
- `ENVIRONMENT`: Environment name (default: `development`)
- `DEBUG`: Debug mode (default: `true`)

Output paths are derived from the repository layout (`utils/gui/out`), and base input files are loaded from `examples/` and the repository `input/` directory.

### Running the Backend

```bash
cd utils/gui
python -m backend.app
```

or from the repository root:

```bash
python -m utils.gui.backend.app
```

The backend will start on `http://localhost:8000`

API documentation available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Frontend Setup

### Prerequisites

- Node.js 18+
- npm or yarn
- Modern web browser

### Installation

```bash
cd frontend
npm install
```

### Development

```bash
npm start
```

The Vite dev server will start on `http://localhost:3000`

### Build for Production

```bash
npm run build
```

## API Documentation

### Catalog Endpoints (prefix: `/api/v1/catalog`)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/v1/catalog/import` | Import catalog from JSON |
| POST | `/api/v1/catalog/validate` | Validate catalog against schema |
| GET | `/api/v1/catalog/presets` | Get list of available presets |
| GET | `/api/v1/catalog/presets/{filename}` | Load specific preset |
| POST | `/api/v1/catalog/packages/functional` | Add functional package |
| PUT | `/api/v1/catalog/packages/functional/{id}` | Update functional package |
| DELETE | `/api/v1/catalog/packages/functional/{id}` | Delete functional package |
| POST | `/api/v1/catalog/packages/os` | Add OS package |
| PUT | `/api/v1/catalog/packages/os/{id}` | Update OS package |
| DELETE | `/api/v1/catalog/packages/os/{id}` | Delete OS package |
| POST | `/api/v1/catalog/packages/infrastructure` | Add infrastructure package |
| PUT | `/api/v1/catalog/packages/infrastructure/{id}` | Update infrastructure package |
| DELETE | `/api/v1/catalog/packages/infrastructure/{id}` | Delete infrastructure package |
| POST | `/api/v1/catalog/packages/driver` | Add driver package |
| PUT | `/api/v1/catalog/packages/driver/{id}` | Update driver package |
| DELETE | `/api/v1/catalog/packages/driver/{id}` | Delete driver package |
| POST | `/api/v1/catalog/packages/miscellaneous` | Add miscellaneous package |
| PUT | `/api/v1/catalog/packages/miscellaneous/{id}` | Update miscellaneous package |
| DELETE | `/api/v1/catalog/packages/miscellaneous/{id}` | Delete miscellaneous package |
| POST | `/api/v1/catalog/layers` | Add functional layer |
| PUT | `/api/v1/catalog/layers/{layerName}` | Update functional layer |
| DELETE | `/api/v1/catalog/layers/{layerName}` | Delete functional layer |

### Catalog Editor Endpoints (prefix: `/api/v1/catalog-editor`)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/v1/catalog-editor/os-packages/bundles` | Get available OS bundles |
| GET | `/api/v1/catalog-editor/os-packages/bundle/{bundleName}` | Get packages in OS bundle |
| GET | `/api/v1/catalog-editor/roles` | Get available roles |
| GET | `/api/v1/catalog-editor/roles/{role}/packages` | Get packages for role |

### Wizard Endpoints (prefix: `/api/v1/config`)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/v1/config/generate-all` | Generate all configuration files |
| GET | `/api/v1/config/generate-all/{job_id}` | Get generation job status |
| POST | `/api/v1/config/download-files` | Download generated files |

### Local Repository Endpoints (prefix: `/api/v1/local-repo`)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/v1/local-repo/generate` | Generate local repository config files |

### Adapter Policy Endpoints (prefix: `/api/v1`)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/v1/adapter-policy` | Get current adapter policy |
| POST | `/api/v1/adapter-policy` | Save adapter policy |
| DELETE | `/api/v1/adapter-policy` | Delete custom adapter policy |

## Configuration Wizard Steps

The Configuration Wizard consists of 9 main steps:

1. **Deployment Setup**: Select cluster type and configure optional features (Cloud-Init, BMC Discovery, Telemetry, Build Stream, GitLab)
2. **PXE Functional Groups**: Configure PXE boot mapping, functional groups, DHCP settings, DNS, and kernel overrides
3. **Network Configuration**: Configure admin and InfiniBand networks, subnets, IP addresses, DNS, and NTP servers
4. **Storage Configuration**: Configure storage mounts, mount profiles, PowerVault iSCSI, swap files, and S3 storage backend
5. **Cloud-Init Configuration**: Configure additional cloud-init `write_files` and `runcmd`
6. **Omnia Cluster Configuration**: Configure Slurm clusters, Kubernetes service clusters, high availability, and security
7. **Telemetry Configuration**: Configure telemetry sources, bridges, sinks, and storage resources
8. **Build Stream Configuration**: Configure BuildStream host and GitLab integration
9. **Summary & Generate**: Review configuration and generate deployment files

### Telemetry Configuration Tabs

The **Telemetry Configuration** step includes tabs for:
- **Sources**: iDRAC, LDMS, DCGM, PowerScale, UFM, VAST, OME
- **Bridges**
- **Sinks**

Storage resource fields are configured within the relevant source and sink tabs.

## Adapter Policy Transformation

The Adapter Policy Module transforms catalog data to adapter policy format based on rules defined in `adapter_policy_default.json`.

### Supported Transformations

- **Field Transformations**: Exclude fields, rename fields
- **Filter Types**: Allowlist filtering, substring filtering
- **Pull Operations**: Pull packages from source files
- **Derived Operations**: Extract common packages, deduplication

### Target Files

- `default_packages.json`: Default OS packages
- `admin_debug_packages.json`: Admin and debug tools
- `openldap.json`: LDAP authentication packages
- `ldms.json`: LDMS monitoring packages
- `ucx.json`: UCX communication library
- `openmpi.json`: OpenMPI packages
- `service_k8s.json`: Kubernetes service packages
- `slurm_custom.json`: Slurm workload manager packages
- `additional_packages.json`: Additional packages from miscellaneous
- `csi_driver_powerscale.json`: CSI driver for PowerScale

## Development

### Backend Development

The backend uses FastAPI with the following structure:

- **Routes**: API endpoint definitions in `api/v1/routes/`
- **Services**: Business logic in `services/`
- **Models**: Data models in `models/`
- **Schemas**: API schemas in `api/v1/schemas/`
- **Core**: Core functionality in `core/`

### Frontend Development

The frontend uses React with the following structure:

- **Features**: Feature-based modules in `src/features/`
- **Components**: Shared components in `src/components/`
- **Hooks**: Custom React hooks in feature directories
- **Stores**: Zustand state management
- **Schemas**: TypeScript/Zod schemas

### State Management

- **Client State**: Zustand with persist middleware
- **Server State**: TanStack Query for API calls
- **Form State**: React Hook Form with Zod validation

## Deployment

### Backend Deployment

```bash
gunicorn utils.gui.backend.app:app -w 4 -k uvicorn.workers.UvicornWorker
```

### Frontend Deployment

```bash
cd frontend
npm run build
# Serve the dist/ directory with nginx or FastAPI static files
```

### Environment Variables

Set the following environment variables:

- `API_TITLE`: API title
- `API_DESCRIPTION`: API description
- `API_VERSION`: API version
- `API_PREFIX`: API endpoint prefix (default: `/api/v1`)
- `HOST`: Server host (default: `0.0.0.0`)
- `PORT`: Server port (default: `8000`)
- `RELOAD`: Auto-reload in development (default: `true`)
- `LOG_LEVEL`: Logging level (default: `info`)
- `CORS_ORIGINS`: Comma-separated allowed CORS origins
- `CORS_ALLOW_CREDENTIALS`: Allow credentials (default: `true`)
- `CORS_ALLOW_METHODS`: Allowed HTTP methods
- `CORS_ALLOW_HEADERS`: Allowed HTTP headers
- `ENVIRONMENT`: Environment name (default: `development`)
- `DEBUG`: Debug mode (default: `true`)

Output paths are derived from the repository layout (`utils/gui/out`), and catalog examples are loaded from `examples/`.

## Troubleshooting

### Common Issues

1. **Backend not starting**: Check Python version and dependencies
2. **Frontend not connecting**: Verify backend URL and CORS settings
3. **Catalog not persisting**: Check JobStore and app.state.catalog initialization
4. **Wizard state lost**: Check localStorage and Zustand persist configuration

### Logs

Backend logs are configured in `backend/config/logging.py` and output to console.

Frontend logs are available in browser developer tools console.

## Documentation

- **Adapter Policy Guide**: `../../build_stream/core/catalog/ADAPTER_POLICY_GUIDE.md`

## License

Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
