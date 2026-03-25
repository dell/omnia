# Validation

The Validation workflow provides comprehensive validation for built images on provided testbeds specified in the PXE mapping file.

## What It Does

The Validation workflow provides:
- **validate_image_on_test** - Validates built images on testbeds
- Testbed deployment from PXE mapping file configuration
- Image boot testing and functionality validation
- Network connectivity and service validation
- Performance and resource utilization testing
- Compliance and security validation on target hardware

## Inputs/Outputs

**Inputs:**
- Built container images from Build Image workflow
- User-specified testbeds from catalog for validation
- PXE mapping file with testbed configurations
- Test validation criteria and test scripts
- Network and hardware specifications
- Expected service configurations

**Outputs:**
- Testbed deployment results and status
- Image boot validation reports
- Service functionality test results
- Performance metrics and benchmarks
- Error diagnostics and troubleshooting guides
- Compliance validation reports

## Key Logic Locations

**Primary Files:**
- `api/validate/routes.py` - HTTP endpoints for validation operations
- `orchestrator/validate/use_cases/` - Validation logic implementations
- `core/validate/entities.py` - Validation domain entities
- `core/validate/repositories.py` - Validation data access
- `core/validate/services.py` - Validation processing services

**Main Components:**
- **ValidateImageOnTestUseCase** - Orchestrates image validation on testbeds
- **PXEMappingParser** - Parses PXE mapping file for testbed configurations
- **TestbedDeployer** - Deploys images to testbeds via PXE
- **ImageBootValidator** - Validates image boot and startup
- **ServiceValidator** - Tests service functionality
- **PerformanceValidator** - Measures performance metrics
- **ComplianceValidator** - Checks compliance on target hardware

## Validation Types

**Image Boot Validation:**
- PXE boot configuration validation
- Image loading and initialization testing
- Kernel and initrd validation
- Boot sequence verification
- Hardware compatibility checking

**Service Validation:**
- Service startup and registration testing
- API endpoint accessibility validation
- Database connectivity verification
- Network service functionality testing
- Inter-service communication validation

**Performance Validation:**
- CPU and memory utilization testing
- Disk I/O and network throughput testing
- Response time and latency measurement
- Load testing and stress testing
- Resource optimization validation

**Compliance Validation:**
- Security policy validation on target hardware
- Regulatory compliance checking
- Configuration standard validation
- Access control verification
- Audit trail validation

## Workflow Flow

1. **Validation Request**: Client submits image validation request with specified testbeds from catalog
2. **PXE Mapping Parsing**: Testbed configurations extracted from PXE mapping file
3. **Testbed Configuration**: User-provided testbeds from catalog are configured for validation
4. **Image Deployment**: Container image deployed to specified testbeds via PXE
5. **Manual PXE Boot**: User runs `set_pxe_boot` utility to boot the images
6. **Boot Validation**: Image boot sequence validated and monitored
7. **Service Testing**: Deployed services tested for functionality
8. **Performance Testing**: Performance metrics collected and analyzed
9. **Compliance Checking**: Security and compliance validation performed
10. **Report Generation**: Comprehensive validation reports created
11. **Result Storage**: Validation results stored for audit trail
12. **Notification**: Validation status notifications sent

## Manual PXE Boot Step

After the `validate_image_on_test` API completes image deployment, users must manually run the `set_pxe_boot` utility from `omnia/utils/set_pxe_boot` to initiate the boot process:

**Required Action:**
```bash
# Run the set_pxe_boot utility from omnia/utils to boot deployed images
omnia/utils/set_pxe_boot --testbed <testbed_id> -i <image_name>
```

**Purpose:**
- Configures PXE boot settings for the deployed images
- Initiates the boot sequence on selected testbeds
- Enables monitoring and validation of the boot process
- Provides manual control over boot timing and test execution

**Parameters:**
- `--testbed`: Target testbed identifier from PXE mapping file
- `-i`: Image name to boot (from validation request)
- Optional: `--timeout`: Boot timeout duration
- Optional: `--debug`: Enable debug logging

**Integration Notes:**
- Must be run after `validate_image_on_test` API completes successfully
- Prepares testbeds for automated boot validation monitoring
- Enables subsequent boot validation, service testing, and performance measurement

## PXE Mapping Management

PXE mapping configuration includes:
- **Testbed Definitions** - Hardware specifications and capabilities
- **Network Configuration** - IP addresses and network settings
- **Boot Parameters** - Kernel parameters and boot options
- **Storage Configuration** - Disk layouts and mount points
- **Validation Criteria** - Test requirements and success criteria

## Security Validation

Security checks include:
- **Image Security Scanning** - Container image vulnerability analysis
- **Testbed Security** - Testbed access control and isolation
- **Network Security** - Network segmentation and firewall validation
- **Data Protection** - Sensitive data protection on testbeds
- **Compliance Checking** - Hardware and software compliance validation

## Quality Assurance

Quality metrics include:
- **Boot Reliability** - Image boot success rate and stability
- **Service Availability** - Service uptime and accessibility
- **Performance Metrics** - Response times and resource utilization
- **Hardware Compatibility** - Hardware driver compatibility and performance
- **Test Coverage** - Validation test completeness and effectiveness

## Integration Points

- Integrates with Build Image workflow for image validation
- Connects to PXE infrastructure for testbed deployment
- Integrates with monitoring systems for performance metrics
- Connects to testbed management systems for hardware control
- Links to compliance systems for regulatory validation

## Configuration

Validation configuration includes:
- PXE mapping file locations and formats
- User-specified testbeds from catalog for validation
- Validation test suites and test scripts
- Performance thresholds and benchmarks
- Compliance rules and security policies

## Error Handling

- Testbed deployment failure diagnostics
- Image boot error analysis and troubleshooting
- Service failure detection and recovery suggestions
- Performance issue identification and optimization recommendations
- Automated testbed recovery and retry mechanisms

## Reporting

Validation reports provide:
- Image validation status summary across testbeds
- Boot performance and reliability metrics
- Service functionality test results
- Performance benchmarks and comparisons
- Hardware compatibility assessment
- Security and compliance validation status
- Troubleshooting guides and recommendations

## Continuous Validation

Ongoing validation includes:
- Automated image testing on new builds
- Periodic testbed health and performance monitoring
- Continuous hardware compatibility validation
- Regular security and compliance checking
- Performance regression testing
- Testbed maintenance and optimization
