# Selected-object editing

## Ground a selection

Prefer a slide number plus named object or original PowerPoint shape ID. Use
`afw.py inspect-pptx` to read the real shape names and IDs from the supplied file.
Generated scene IDs survive in PPTX object names. Verify that a selected name exists
in the source scene. Do not confuse app annotation IDs, PowerPoint IDs and scene IDs.
A screenshot rectangle is a clue: inspect its content and identify exact scene objects
before executing an edit; ask when the intended object is ambiguous.

For a tracked run, `workflow.py selection-request` verifies both source-scene and final
PPTX fingerprints against the current exported map, then resolves `--name` or native
`--shape-id`. It refuses mismatches. `workflow.py edit` preserves the prior scene and
returns the session to export/checking. See `workflow-session.md` for runnable examples.

Record scene_id, selected_ids, expected_sha256 and operations. `selection_edit.py`
applies `{"op":"move","dx":10,"dy":0}` or
`{"op":"set","properties":{"fill":"#345678"}}` to selected objects.
The original file is preserved; use a new output path for each revision.

## Protected scope

Only selected IDs may change, except attached connector endpoints that must follow
moved shapes. Report those connectors separately. Locked objects cannot change.
Science-bearing colors require explicit `allow_semantic_color: true`; explain any
changed mapping. Text edits trigger scientific review in the audit, not an automatic
claim of correctness. Inspect for overlap after movement even when boundary checks pass.

## Verify and continue

Review the audit sidecar and before/after previews. Re-export the scene to SVG/PPTX,
not from an old generator default. A manual PPTX edit may not be reflected in the
scene: compare/import it intentionally and preserve the user's edited file.
The first release supplies the selection translation and safe edit operation, not
a background listener in PowerPoint or automatic screenshot understanding.

For a before/after demonstration, change the color of one non-semantic title or move
one label slightly. Test multi-select and a connected shape in isolated fixtures.
Do not use a decorative change as evidence that all complex edits are safe.
