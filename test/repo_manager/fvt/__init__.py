"""
Repo Manager — Functional Verification Tests.

Each tag directory contains:
    test_playbook.py   — deploys ``repo_manager.yml --tags <tag>``
    <suite>/           — post-deployment verification tests

Tag directories:
    precheck/          config/
    prepare/           pulp/
    execute/           repos/, artifacts/, policy/
    status/            status/
    cleanup/           cleanup/
    cleanup_repos/     selective/
    catalog_generate/  generate/
    catalog_add/       add/
    catalog_delete/    delete/
    catalog_validate/  validate/
    user_registry/     validation/
"""
