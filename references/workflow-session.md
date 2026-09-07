# Persistent figure work

The agent conducts the visual/scientific work. These commands preserve its inputs,
versions and evidence across turns; they do not call an image service, understand a
paper, watch PowerPoint, or approve designs on the user's behalf.

## One session per figure

Keep the session under `.local/`. Prepare a brief with `title`, `scientific_source`,
`mechanism`, `must_show`, `must_not_show`. Add useful optional fields such as
`allowed_labels`, `input_output`, `style`, `paper_width_mm`, `schematic_quantities`.
The paper controls topology, equations, training/inference distinctions and claims.
For a reusable schematic, state the mathematical example and its limitations instead.

```sh
python3 scripts/workflow.py init --run .local/runs/my-figure --brief .local/my-brief.json
python3 scripts/workflow.py add --run .local/runs/my-figure --id paper-v1 --role source --path .local/paper.tex
python3 scripts/workflow.py status --run .local/runs/my-figure
```

The saved history is append-only. Resume with `status`; do not rebuild from an old
generator default. Changed source files invalidate the relevant evidence. Register
new paper/reference versions using `add ... --replaces old-id`; previous records stay
in history. If the brief itself changes, start a new session so prior approvals cannot
silently acquire a different scientific meaning.

## Reference selection and visual exploration

Use `afw.py search ... --include-private` to find relevant registered images, not an
arbitrary component with a matching keyword. Inspect each selected image. Its role is
style, compatible mechanism, or literal asset. Unknown licenses remain private.
Read `design-and-priors.md` for registration and prompt preparation. Attach the chosen
reference or its exact prepared manifest with `add --role reference`.

Pass `image-tool-input.json` through the current image skill's supported image-attachment
mechanism. The helper merely prepares it. No CLI command here authorizes uploading a
private image or publishing it. Label model outputs `candidate`; store the actual image
and prompt. A design review can reject or revise it without replacing an accepted file.

```sh
python3 scripts/workflow.py add --run .local/runs/my-figure --id concept-v1 --role candidate --path .local/concept-v1.png
python3 scripts/workflow.py approve --run .local/runs/my-figure --id concept-v1 --user-evidence 'Exact user acceptance from the conversation'
```

Only run `approve` after that acceptance actually exists. An explicit request to use
a reference is evidence for that reference's selection, not for every derived image.
Native-first work may omit a generated candidate; image generation is not a mandatory
extra step for a straightforward existing-scene edit.

## Editable reconstruction and checks

Rebuild required diagram elements as named native objects. Store a scene, export a
NEW PPTX and render its preview under the active presentations skill. Do not put a
whole diagram screenshot in the PPTX and call it editable.

```sh
python3 scripts/workflow.py add --run .local/runs/my-figure --id scene-v1 --role scene --path .local/scene-v1.json
node scripts/export_components.mjs --scene .local/scene-v1.json --output .local/runs/my-figure/output/figure-v1.pptx --build-dir .local/runs/my-figure/build
python3 scripts/workflow.py add --run .local/runs/my-figure --id deck-v1 --role pptx --path .local/runs/my-figure/output/figure-v1.pptx --slide 1
python3 scripts/workflow.py add --run .local/runs/my-figure --id preview-v1 --role preview --path .local/runs/my-figure/output/figure-v1-previews/scene-id.png
python3 scripts/workflow.py validate-native --run .local/runs/my-figure
```

Use the actual preview filename returned by the exporter.
The output and build directories must be separate sibling subdirectories. Pass
`--build-dir` for an isolated test or session; otherwise private build files default
to the project's `.local/build`. Do not use the `.local/` root itself as the output
directory, since it would contain that build directory.

Multi-page files can serve
separate figure sessions by binding each to its correct slide. Mixed canvas sizes
are rejected. The map beside the exported PPTX ties each native ID and name to exact
scene and PPTX fingerprints. A hand-edited PPTX requires intentional reconciliation,
not reuse of a stale map.

After performing each check, record its concrete scope:

```sh
python3 scripts/workflow.py check --run .local/runs/my-figure --kind scientific --evidence 'Which equations, paths, meanings and assumptions were checked'
python3 scripts/workflow.py check --run .local/runs/my-figure --kind visual --evidence 'Which final render and use-size preview were inspected, and which issues were repaired'
python3 scripts/workflow.py check --run .local/runs/my-figure --kind selection --evidence 'Actual one-object edit trial and unchanged protected objects'
```

These commands record reviewer evidence; they do not perform automatic scientific or
visual evaluation. Use `--verdict fail` for an unresolved issue. Do not paste example
evidence without conducting the check. Native validation proves object correspondence,
not appearance. Figure acceptance and check results remain separate, bound to versions.
When a checked draft has no user acceptance yet, deliver it for review rather than
inventing an approval to make the status green.

## Selected-region feedback

Read `local-editing.md`. Resolve app comments to a current slide and named object by
inspection. Native file IDs are usable only after version verification. Screenshot
rectangles require visual grounding; their coordinates do not automatically identify
an exact object. If ambiguous, ask a concise question about that region.

```sh
python3 scripts/workflow.py selection-request --run .local/runs/my-figure --name target-label --operation '{"op":"move","dx":0,"dy":8}' --output .local/runs/my-figure/move-label.json
python3 scripts/workflow.py edit --run .local/runs/my-figure --request .local/runs/my-figure/move-label.json --id scene-v2
```

Multiple `--name` or native `--shape-id` arguments support multi-selection. The request
records a source fingerprint. Only selected objects and necessary attached endpoints
change. Arrowheads stored as separate shapes require explicit matching selection when
moving the whole arrow. Preserve scientific color mappings.
For an explicitly authorized change to science-bearing colors, add
`--allow-semantic-color` and review the meaning of the new mapping; ordinary color
changes must not silently bypass this check. Re-export the new scene,
inspect the resulting PPTX and compare protected regions. New scene versions invalidate
old export/check bindings; repeat only the checks affected by the change.

## Finish and reusable learning

Deliver editable PPTX plus final-size preview and requested vector output. Save useful
accepted examples in the private reference registry; do not change their scientific
meaning when later using them as style priors. Record rejection reasons so old disliked
designs do not return through default retrieval. Publication, paper integration,
installation and social posting are separate user-authorized actions.
