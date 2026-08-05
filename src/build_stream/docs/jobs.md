# Jobs Management

The Jobs workflow manages the complete lifecycle of build jobs in Build Stream, from creation through completion and monitoring.

## What It Does

The Jobs workflow provides:
- Job creation with idempotency guarantees
- Stage-based execution with state management
- Job monitoring and status tracking

## Inputs/Outputs

**Inputs:**
- Job creation requests with stage definitions
- Authentication tokens for security
- Optional job parameters and configuration

**Outputs:**
- Job IDs for tracking
- Stage execution results
- Audit events for compliance
- Error details and diagnostics

## Key Logic Locations

**Primary Files:**
- `api/jobs/routes.py` - HTTP endpoints for job operations
- `orchestrator/jobs/use_cases/create_job.py` - Job creation business logic
- `core/jobs/entities.py` - Job and Stage domain entities
- `core/jobs/repositories.py` - Data access layer
- `core/jobs/services.py` - Job-related domain services

**Main Components:**
- **CreateJobUseCase** - Handles job creation with validation
- **JobRepository** - Manages job persistence
- **StageRepository** - Manages stage state tracking
- **ResultPoller** - Handles async result collection

## Workflow Flow

1. **Job Creation**: Client submits job via `/api/v1/jobs` endpoint
2. **Validation**: Request validated for authentication and schema
3. **Idempotency Check**: Prevents duplicate job creation
4. **Stage Initialization**: Job broken into executable stages
5. **Async Execution**: Stages queued for background processing
6. **Status Updates**: Job status tracked through state transitions
7. **Result Collection**: Results polled and stored
8. **Audit Logging**: All operations logged for traceability

## Prerequisites

To run jobs, the following infrastructure components are required:

- **PostgreSQL Database**: Used for persistent storage of job metadata and status
- **S3-compatible Object Storage**: Utilized for storing build artifacts, such as catalog files and build images  
- **Message Queue (e.g., RabbitMQ, Kafka)**: Enables asynchronous communication between job components and facilitates scalable processing
- **Container Runtime (e.g., Docker, containerd)**: Required for building and validating container images

These components must be properly configured and accessible to the BuildStreaM service for successful job execution.

## API Documentation

- See Omnia ReadTheDocs for complete API documentation
- Local development docs: `http://localhost:${PORT}/docs`
- Local ReDoc: `http://localhost:${PORT}/redoc`

## Stage Types

Jobs support multiple stages:
- **parse-catalog** - Software catalog processing
- **generate-input-files** - Input file generation
- **create-local-repository** - Local repository creation
- **build-image-x86_64** - x86_64 OS image building
- **build-image-aarch64** - aarch64 OS image building
- **validate-image-on-test** - Image validation testing

## Error Handling

- Invalid state transitions are rejected
- Comprehensive error reporting with context
- Audit trail captures all error events
