"""
Repo Manager — Functional Verification Tests.

Each tag directory contains:
    test_playbook.py   — deploys ``repo_manager.yml --tags <tag>``
    <suite>/           — post-deployment verification tests
    negative/          — negative/error scenario tests (where applicable)

Tag directories:
    precheck/          config/, negative/
    prepare/           pulp/, negative/
    execute/           repos/, artifacts/, policy/, negative/
    status/            status/, negative/
    cleanup/           cleanup/, negative/
    cleanup_repos/     selective/
    catalog_generate/  generate/, negative/
    catalog_add/       add/, negative/
    catalog_delete/    delete/, negative/
    catalog_validate/  validate/
    user_registry/     validation/
"""
