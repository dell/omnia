# Build Stream Documentation

This directory contains comprehensive documentation for the Build Stream module and its workflows.

## Documentation Structure

### Overview Documentation
- **[Architecture](./architecture.md)** - Domain architecture, layers, and design
- **[Design](./design/build-stream-design.md)** - Detailed domain design and structure
- **[Main README](../README.md)** - High-level overview and getting started guide
- **[Input Contract](./contracts/input-contract.md)** - Input file specification
- **[Output Contract](./contracts/output-contract.md)** - Output artifact specification

### Workflow Documentation
- **[Jobs Management](./jobs.md)** - Job lifecycle and orchestration
- **[Catalog Processing](./catalog.md)** - Software catalog parsing and role generation
- **[Local Repository](./local_repo.md)** - Local package repository creation
- **[Image Building](./build_image.md)** - Container image build workflows
- **[Validation](./validation.md)** - Input and output validation

## Quick Navigation

### For New Contributors
1. Start with the [main README](../README.md) for architecture overview
2. Read the [Architecture](./architecture.md) document for detailed understanding
3. Explore specific workflow documentation based on your area of focus

### For Debugging Issues
1. Check the relevant workflow documentation for your issue area
2. Use the Architecture document to trace the failing component
3. Review the audit trail and logging sections

### For Feature Development
1. Read the Architecture document for design and patterns
2. Review the relevant workflow documentation
3. Follow the documentation standards below

## Documentation Standards

All Build Stream documentation follows these standards:
- **No sensitive data** - Never include passwords, tokens, or secrets
- **Developer-focused** - Written for technical contributors
- **Cross-referenced** - Links between related documentation
- **Example-driven** - Includes practical examples and code snippets
- **Maintainable** - Easy to update as the codebase evolves

## Getting Help

If you need additional help beyond the documentation:
1. Check the troubleshooting sections in workflow docs
2. Review the audit trail and error handling patterns
3. Consult the architecture diagrams in the Architecture document
4. Reach out to the Build Stream development team

## Contributing to Documentation

When contributing to Build Stream:
1. Update relevant documentation for API changes
2. Add new workflow documentation for new features
3. Keep cross-references up to date
4. Follow the established documentation standards
5. Include examples and troubleshooting information
