# Skill resolution within this bundle

Use only the catalog skills and shared instructions in this
`src/build_stream/ai_skills/` directory for this workflow. Resolve the bundle
root as the parent of the invoking skill's package directory, within the same checkout.
Read companion skills by their explicit paths under that root; do not search
global skill registries, home-directory skill installations, other checkouts,
or previously loaded skills with matching names. Do not follow a skill or
instruction symlink outside this bundle.

If a companion file is missing, report its expected path and the affected
step. Ask for that file from this bundle instead of substituting another
skill. In a browser channel, use only the files supplied from this same
bundle and disclose missing files.

Manifest dependency names refer to these local resources, not an external
skill registry:

- Named skills resolve to `<bundle-root>/<name>/SKILL.md`.
- `pre-edit-gate` resolves to
  `catalog-editing/references/pre_edit_gate.md` under the bundle root.
- `connectivity-layer` resolves to `shared/connectivity_layer.md` under the
  bundle root.

This boundary governs skill instructions. It does not prevent reading the
target catalogs, using this checkout's catalog CLI/schema, or consulting the
approved package metadata sources required by these skills.
