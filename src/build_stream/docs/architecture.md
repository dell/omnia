# Build Stream Domain Architecture

> **Version**: Omnia 3.0
> **Last Updated**: 2026-09-03
> **Domain**: build_stream (omnia.build_stream)

## Overview

The Build Stream domain provides a FastAPI-based RESTful service that orchestrates software catalog parsing, local repository creation, image building, and CI/CD pipelines via GitLab CE. It serves as the central orchestration engine for Omnia's build and deployment workflows.

## Architecture Components

### 1. BuildStream Manager (BSM) API
- **Technology**: FastAPI + PostgreSQL
- **Purpose**: RESTful API for job orchestration
- **Endpoints**: Build, Deploy, Boot, Validate, Catalog parsing, Artifact management
- **Container**: `omnia_build_stream:latest`

### 2. Playbook Watcher Service
- **Technology**: Python + systemd
- **Purpose**: Monitors playbook execution requests and routes to BSM API
- **Integration**: Listens for playbook completion events

### 3. GitLab Integration
- **Purpose**: CI/CD pipeline orchestration
- **Components**: 
  - GitLab CE deployment
  - CI/CD pipeline configuration
  - Catalog repository management
  - Artifact upload and management

### 4. PostgreSQL Database
- **Purpose**: Job state management and audit trail
- **Schema**: Jobs, Stages, Artifacts, Audit events
- **Features**: Transactional integrity, audit logging

## Data Flow

```
┌─────────────┐
│   GitLab     │
│   CI/CD      │
└──────┬──────┘
       │
       │ HTTP/Webhook
       ▼
┌─────────────┐
│   BSM API    │
│  (FastAPI)   │
└──────┬──────┘
       │
       │ Database
       ▼
┌─────────────┐
│ PostgreSQL  │
└─────────────┘
```

## Key Features

1. **Job Orchestration**: Create, monitor, and manage build/deploy jobs
2. **Catalog Parsing**: Validate and parse software catalog JSON files
3. **Local Repository**: Create and manage local package repositories
4. **Image Building**: Orchestrate OS image building via image_build_manager
5. **Artifact Management**: Upload and manage deployment artifacts
6. **Audit Logging**: Track all operations for compliance and debugging

## Integration Points

### Upstream Dependencies
- **repo_manager**: Consumes `repo_status.yml` for package availability
- **image_build_manager**: Consumes `build_status.yml` for image availability

### Downstream Consumers
- **orchestrator**: Consumes `build_stream_status.yml` for API endpoints
- **CI/CD pipelines**: Uses BSM API for build/deploy orchestration
- **Operators**: Uses BSM API for manual job management

## Configuration

### Input Files
- `build_stream_config.yml`: Main configuration for BSM API
- `build_stream_credentials.yml`: GitLab and database credentials

### Output Files
- `build_stream_status.yml`: API endpoints and status
- Job logs: Per-job execution logs in `/opt/omnia/log/build_stream/`

## Security Considerations

1. **JWT Authentication**: BSM API uses JWT tokens for authentication
2. **Ansible Vault**: Credentials stored in Ansible Vault
3. **TLS/SSL**: HTTPS for API communication
4. **Audit Logging**: All operations logged for compliance

## Deployment Architecture

The Build Stream domain is deployed on the Omnia Infrastructure Manager (OIM) node and consists of:

1. **BSM Container**: FastAPI service (port 8010)
2. **PostgreSQL Database**: Data persistence
3. **GitLab CE**: CI/CD orchestration
4. **Playbook Watcher**: systemd service for playbook monitoring

## Scalability Considerations

- **Horizontal Scaling**: BSM API can be scaled horizontally
- **Database Connection Pooling**: PostgreSQL connection pooling
- **Job Queue**: Asynchronous job processing
- **Load Balancing**: Can be placed behind load balancer

## Monitoring and Observability

- **Health Endpoint**: `/health` for liveness/readiness probes
- **Metrics**: Job statistics, API performance metrics
- **Logging**: Structured logging via `log_secure_info`
- **Audit Trail**: Complete audit trail of all operations

## Upgrade and Rollback

The domain includes upgrade and rollback playbooks for:
- BSM API container updates
- PostgreSQL schema migrations
- GitLab version upgrades
- Configuration updates

## Troubleshooting

Common issues and solutions:
1. **BSM API not responding**: Check container status and logs
2. **Database connection errors**: Verify PostgreSQL credentials and connectivity
3. **GitLab integration issues**: Check GitLab API tokens and permissions
4. **Job failures**: Review job logs and audit trail
