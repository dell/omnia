# Build Stream

**Build Stream** is a **RESTful API** (Representational State Transfer Application Programming Interface) service that orchestrates the creation and management of build jobs for the Omnia infrastructure platform. It provides a centralized interface for managing software catalog parsing, local repository creation, image building, and validation workflows.

## Architecture Overview

Build Stream follows a clean architecture pattern with clear separation of concerns:

- **API Layer** (`api/`): FastAPI routes and HTTP handling
- **Core Layer** (`core/`): Business logic, entities, and domain services  
- **Orchestrator Layer** (`orchestrator/`): Use cases that coordinate workflows
- **Infrastructure Layer** (`infra/`): External integrations and data persistence
- **Common Layer** (`common/`): Shared utilities and configuration

## High-Level Workflow

1. **Authentication**: **JWT** (JSON Web Token)-based authentication secures all API endpoints
2. **Job Creation**: Clients submit build requests through the jobs API
3. **Stage Processing**: Jobs are broken into stages (catalog parsing, local repo, build image, validation)
4. **Async Execution**: Stages execute asynchronously with result polling
5. **Artifact Management**: Build artifacts are stored and tracked throughout the process
6. **Audit Trail**: All operations are logged for traceability and compliance

## Configuration

Configuration is managed through:
- Environment variables for runtime settings
- `build_stream.ini` for artifact store configuration
- Vault integration for secure credential management
- Database configuration for persistent storage

Key configuration areas:
- Database connections (PostgreSQL)
- Artifact storage backend (file system or in-memory)
- Vault endpoints and authentication
- **CORS** (Cross-Origin Resource Sharing) and server settings

## Getting Started

### For Developers

**Primary Entry Points:**
- `main.py` - FastAPI application entry point
- `api/router.py` - API route aggregation
- `container.py` - Dependency injection setup

**Key Workflows:**
- [Jobs Management](./doc/jobs.md) - Job lifecycle and orchestration
- [Catalog Processing](./doc/catalog.md) - Software catalog parsing and role generation  
- [Local Repository](./doc/local_repo.md) - Local package repository creation
- [Image Building](./doc/build_image.md) - Container image build workflows
- [Validation](./doc/validation.md) - Input and output validation

**Development Setup:**
```bash
# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Set environment variables
export HOST=<host ip>
export PORT=<port>

# Run development server
uvicorn main:app --reload

# Run tests
pytest
```

**API Documentation:**
- See Omnia ReadTheDocs for complete API documentation

### Architecture Components

**Core Services:**
- **Job Service**: Manages job lifecycle and state transitions
- **Catalog Service**: Parses software catalogs and generates roles
- **Local Repo Service**: Creates and manages local repositories
- **Build Service**: Orchestrates container image builds
- **Validation Service**: Validates inputs and outputs

**Data Flow:**
1. Client requests → API routes → Use cases → Core services → Repositories
2. Async job processing with stage-based execution
3. Result polling and webhook notifications
4. Artifact storage and metadata tracking

**Security:**
- JWT token-based authentication
- Vault integration for secret management
- Role-based access control
- Audit logging for compliance

## Workflow Areas

Each major workflow area has dedicated documentation:

- **Jobs** - Job creation, monitoring, and lifecycle management
- **Catalog** - Software catalog parsing and role generation
- **Local Repo** - Local package repository setup and management  
- **Build Image** - Container image build orchestration
- **Validation** - Input validation and output verification

See the `doc/` directory for detailed workflow documentation.

## Dependencies

Build Stream uses FastAPI with the following key dependencies:
- FastAPI/Uvicorn for web framework
- SQLAlchemy for database **ORM** (Object-Relational Mapping)
- Dependency Injector for **IoC** (Inversion of Control) container
- PyJWT for **JWT** (JSON Web Token) authentication
- Ansible for infrastructure automation
- Vault client for secret management

## Support

For troubleshooting and development guidance:
1. Check the workflow-specific documentation in `doc/`
2. Review API logs for error details
3. Consult the audit trail for job execution history
4. Refer to the health check endpoint: `/health`

