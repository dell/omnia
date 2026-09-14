"""Target-side path resolution for Build Stream automation."""

from omnia_auto import (
    read_remote_env,
    resolve_domain_data_path,
    resolve_domain_input_path,
)

from ..vars.common_vars import (
    DOMAIN_NAME,
    ENV_OMNIA_DATA_PATH,
    ENV_OMNIA_PROJECT_NAME,
)


def resolve_build_stream_data_path(host) -> str:
    """Resolve the Build Stream data root from the execution OIM."""
    return resolve_domain_data_path(
        host,
        DOMAIN_NAME,
        ENV_OMNIA_DATA_PATH,
    )


def resolve_omnia_data_path(host) -> str:
    """Resolve the Omnia data root from the execution OIM."""
    path = read_remote_env(host, ENV_OMNIA_DATA_PATH).rstrip("/")
    if not path.startswith("/") or path == "":
        raise ValueError("OMNIA_DATA_PATH must resolve to an absolute path")
    return path


def resolve_build_stream_input_path(host) -> str:
    """Resolve the current project input directory from the execution OIM."""
    return resolve_domain_input_path(
        host,
        DOMAIN_NAME,
        ENV_OMNIA_DATA_PATH,
        ENV_OMNIA_PROJECT_NAME,
    )
