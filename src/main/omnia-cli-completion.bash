#!/bin/bash

# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# =============================================================================
# Bash completion for omnia-cli
# =============================================================================
# Install:
#   cp omnia-cli-completion.bash /etc/bash_completion.d/omnia-cli
# Or source manually:
#   source omnia-cli-completion.bash
#
# Installed automatically by: omnia.sh --setup-venv
# =============================================================================

_omnia_cli_completions() {
    local cur prev words cword
    _init_completion || return

    # All top-level commands
    local commands="status check edit logs repo_manager image_build_manager \
orchestrator discovery telemetry build_stream utils version help"

    # All domain names (used by edit, logs, help, and as direct commands)
    local domains="repo_manager image_build_manager orchestrator discovery \
telemetry build_stream utils"

    # Determine which command was typed (skip flags and their values)
    local command=""
    local i
    for ((i = 1; i < cword; i++)); do
        case "${words[i]}" in
            --project|-p)
                ((i++))  # skip the project value
                ;;
            -*)
                ;;
            *)
                if [ -z "$command" ]; then
                    command="${words[i]}"
                fi
                ;;
        esac
    done

    # Complete --project value: auto-discover project names from disk
    if [ "$prev" = "--project" ] || [ "$prev" = "-p" ]; then
        local data_path="${OMNIA_DATA_PATH:-/opt/omnia}"
        local projects=()
        if [ -d "$data_path" ]; then
            local dir
            for dir in "$data_path"/*/input/*/; do
                if [ -d "$dir" ]; then
                    local pname
                    pname=$(basename "$dir")
                    local found=0
                    local p
                    for p in "${projects[@]+"${projects[@]}"}"; do
                        [ "$p" = "$pname" ] && found=1 && break
                    done
                    [ "$found" -eq 0 ] && projects+=("$pname")
                fi
            done
            for dir in "$data_path"/*/output/*/; do
                if [ -d "$dir" ]; then
                    local pname
                    pname=$(basename "$dir")
                    local found=0
                    local p
                    for p in "${projects[@]+"${projects[@]}"}"; do
                        [ "$p" = "$pname" ] && found=1 && break
                    done
                    [ "$found" -eq 0 ] && projects+=("$pname")
                fi
            done
        fi
        if [ "${#projects[@]}" -gt 0 ]; then
            COMPREPLY=($(compgen -W "${projects[*]}" -- "$cur"))
        fi
        return
    fi

    # No command yet — complete commands
    if [ -z "$command" ]; then
        COMPREPLY=($(compgen -W "$commands" -- "$cur"))
        return
    fi

    # Command is set — complete based on context
    case "$command" in
        edit|logs|log|help)
            # These commands take a domain as the next positional arg
            local has_domain=0
            for ((i = 1; i < cword; i++)); do
                case "${words[i]}" in
                    --project|-p)
                        ((i++))
                        ;;
                    edit|logs|log|help)
                        ;;
                    -*)
                        ;;
                    *)
                        if [ "${words[i]}" != "$command" ]; then
                            has_domain=1
                        fi
                        ;;
                esac
            done
            if [ "$has_domain" -eq 0 ]; then
                COMPREPLY=($(compgen -W "$domains" -- "$cur"))
            else
                # Domain already provided — offer --project
                if [[ "$cur" == -* ]]; then
                    COMPREPLY=($(compgen -W "--project" -- "$cur"))
                fi
            fi
            ;;
        status|check|repo_manager|image_build_manager|orchestrator| \
        discovery|telemetry|build_stream|utils)
            # These commands only take --project
            if [[ "$cur" == -* ]]; then
                COMPREPLY=($(compgen -W "--project" -- "$cur"))
            fi
            ;;
        version)
            # No further args
            ;;
    esac
}

complete -F _omnia_cli_completions omnia-cli
complete -F _omnia_cli_completions ./omnia-cli
