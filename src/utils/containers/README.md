# Containers

This directory is reserved for container-related assets used by the utils domain.

## Purpose

The utils domain may use container images for log collection, ISO building, or other utility operations in the future. This directory provides a standardized location for:

- Containerfiles (Dockerfile/Podmanfile)
- Container build scripts
- Container configuration files
- Container-related documentation

## Structure

```
containers/
├── README.md
└── <container_name>/
    ├── Containerfile.<os_version>
    ├── requirements.txt
    ├── build.sh
    └── README.md
```

## Current State

The utils domain currently does not build or use custom containers. All operations are performed directly on the host system or through standard Ansible modules. This directory is provided for future extensibility and Galaxy collection compliance.

## Future Use Cases

Potential container use cases for the utils domain:

- **Log Collection**: Containerized log aggregation tools
- **ISO Building**: Containerized image build environments
- **Validation**: Containerized configuration validation tools

## License

Apache License, Version 2.0
