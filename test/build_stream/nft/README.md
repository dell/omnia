# Build Stream isolated source tests

This directory retains the pre-existing isolated Build Stream API, core,
infrastructure, and orchestrator tests under `unit/`, together with their
fixtures and helper modules.

The former Local Repository performance cases have been removed. There are no
registered Build Stream NFT performance cases in the automation catalog.

The isolated source tests use their local pytest configuration and are not part
of the 71 Build Stream FVT cases documented in `../fvt/README.md`.
