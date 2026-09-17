"""Target-side path resolution for Build Stream automation."""

from pathlib import PurePosixPath

from omnia_auto import (
    read_remote_env,
    resolve_domain_data_path,
    resolve_domain_input_path,
)

from ..vars.common_vars import (
    DOMAIN_NAME,
    ENV_OMNIA_DATA_PATH,
    ENV_OMNIA_PROJECT_NAME,
    ENV_OMNIA_VENV_PATH,
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


def resolve_omnia_path(host, *relative_parts: str) -> str:
    """Resolve a path below ``OMNIA_DATA_PATH`` on the execution OIM."""
    base_path = PurePosixPath(resolve_omnia_data_path(host))
    clean_parts = []
    for part in relative_parts:
        candidate = PurePosixPath(str(part))
        if not candidate.parts or candidate.is_absolute() or any(
            item in {"", ".", ".."} for item in candidate.parts
        ):
            raise ValueError(
                "Omnia relative path contains an unsafe component"
            )
        clean_parts.extend(candidate.parts)
    return str(base_path.joinpath(*clean_parts))


def resolve_omnia_venv_path(host) -> str:
    """Resolve ``OMNIA_VENV_PATH`` from the execution OIM environment."""
    path = read_remote_env(host, ENV_OMNIA_VENV_PATH).rstrip("/")
    if not path.startswith("/") or path == "/":
        raise ValueError(
            "OMNIA_VENV_PATH must resolve to a safe absolute path"
        )
    return path


def resolve_build_stream_input_path(host) -> str:
    """Resolve the current project input directory from the execution OIM."""
    return resolve_domain_input_path(
        host,
        DOMAIN_NAME,
        ENV_OMNIA_DATA_PATH,
        ENV_OMNIA_PROJECT_NAME,
    )
