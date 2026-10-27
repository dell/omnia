# catalog-selection-gate

## Purpose

Validates an operator-requested `os_version`/`architecture`/`stack`/`node_role`/`gpu`/`storage`/`network` selection against the Selection Catalogue's `support_status` before any functional group or package set is emitted. Use when Catalog Generation, Catalog Editing, or an Analysis skill is about to resolve or present a selection on one of those axes.

## When to Use

Use this skill when you need to:
- Present a menu of choices on a Selection Catalogue axis (`os_version`, `architecture`, `stack`, `node_role`, `gpu`, `storage`, `network`)
- Decide whether an operator-requested selection is `supported`, `planned`, or `unsupported`
- Look up the master reference file's Appendix A tables for downstream catalog generation, editing, or analysis
- Regenerate `references/master_reference_file.md` after the shipped catalogs or repository configuration change

## Prerequisites

- `references/master_reference_file.md` (in this package) — the A.1–A.8 Appendix A tables

## Usage

This is not an operator-invoked skill on its own — it is a shared decision procedure that Catalog Generation, Catalog Editing, and the Analysis skills each call before emitting a functional group or package set.

## Capabilities

| Capability | Description |
|------------|-------------|
| Supported-Only Menus | Never presents a `planned`/`unsupported` option in a menu |
| Allow/Refuse Decision | Allows `supported` selections, refuses `planned`/`unsupported` ones with named alternatives |
| No Silent Substitution | Never substitutes an alternative for the operator without explicit confirmation |
| No Fabrication | Flags a selection absent from the table rather than guessing its support status |
| Offline Disclosure | States plainly when a decision was made from the master reference file, not a live source |

## References

- `references/master_reference_file.md` — the 8 Appendix A tables this gate and every consuming skill read

## Workflow

1. **Determine the axis** the requested/presented selection falls on
2. **Read the A.1 Selection Catalogue table** in full for that axis
3. **Find the matching row** (case-insensitive)
4. **No match:** flag for manual review, do not fabricate
5. **`supported` match:** allow the selection
6. **`planned`/`unsupported` match:** refuse, state the recorded status, and list only the `supported` alternatives on that axis
7. **Disclose** whenever the decision was made offline

## Limitations

- Not a standalone operator-facing skill — always invoked by another skill
- Does not automate re-derivation of `references/master_reference_file.md`; regeneration is a manual, documented process
