# Dataset: data_set_01

Default test dataset for build_stream FVT.

## Contents

```
data_set_01/
└── input/
    └── build_stream_config.yml   # Build stream domain configuration
```

## Usage

This dataset is synced to the target server when `sync_build_stream_input: true`
in `test_config.yml`. Files are placed at:

```
<OMNIA_DATA_PATH>/build_stream/input/<OMNIA_PROJECT_NAME>/
```

## Customization

Edit `input/build_stream_config.yml` to match your test environment.
Set `enable_build_stream: true` to enable the domain for testing.
