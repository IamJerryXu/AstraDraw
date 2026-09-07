# Assistant-authored design plans

A design plan records decisions made after the assistant reads the scientific
brief and inspects any selected images. The compiler checks the recorded structure
and turns it into concrete drawing instructions. It does not read a paper, infer
its method, verify equations, or decide that a reference mechanism is scientifically
compatible. The assistant must check every source statement and visual encoding
against the paper before preparing the plan, and inspect the generated figure
afterward. A passing structural check is not scientific or aesthetic approval.

## Compile one selected composition

Run these examples from the skill folder. They are original fictional teaching
material and require no reference images or private files:

```sh
python3 scripts/afw.py priors --brief examples/design-brief.json --design-plan examples/design-plan.json --output-dir .local/design-example-stacked
python3 scripts/afw.py priors --brief examples/design-brief.json --design examples/design-plan.json --layout side-by-side --output-dir .local/design-example-side
```

`--design` and `--design-plan` are equivalent. Without `--layout`, the compiler uses
`recommendation`; an explicit layout ID overrides that choice. Each invocation
compiles exactly one composition into one generation prompt. Alternative layouts
in the plan are choices, not instructions to put two candidate figures into one
image. One layout is sufficient; the example contains two to demonstrate selection.

`--style` is optional. When absent it comes from `style.profile`; when explicitly
provided it must agree with the plan. `--layout` without a plan is rejected. Existing
calls that select only a reference or legacy component still work without a plan.
The output directory must not already exist.

For inspected registered references, add one `--reference-id ID` per image and
assign all of them in `reference_jobs`. Existing reference permissions and approval
checks still apply; this option does not grant upload or publication permission.
With a design plan, all actual attachments must have jobs tied to explicit
`--reference-id` values. Do not mix in legacy `--component` or `--private-asset`
attachments that lack such assignments. A plan without references uses
`reference_jobs: []`; its image input omits `referenced_image_paths`.

The command writes a readable `prompt.txt`, matching `image-tool-input.json`, and
`manifest.json`. It does not call image generation. The manifest records the exact
brief digest, `design_plan_sha256`, chosen `layout_id`, actual image references,
and the prepared-not-generated status. The prompt translates regions, emphasis,
connections, zoom pairs, reference jobs, and visual grammar into instructions;
it does not merely append the plan as JSON. Specific fonts and palette assignments
take precedence over generic style examples.

## Complete version 1 fields

All fields listed below are required unless explicitly marked optional. Strings
must be nonempty. Arrays may be empty only where stated. Additional fields are not
interpreted by the compiler; keep essential design decisions in the documented
fields. See [the runnable plan](../examples/design-plan.json) for the exact nesting.

| Top-level field | Value and purpose |
| --- | --- |
| `version` | Integer `1`. |
| `reader_question` | The question the reader should answer by looking at the figure. |
| `main_message` | One concrete conclusion that the composition makes visible. |
| `brief_sha256` | SHA-256 of the exact scientific brief file bytes. Any file change, including formatting, requires a reviewed new binding. |
| `method_graph` | The paper-grounded nodes and scientific connections described below. |
| `layouts` | One or more alternative compositions, each with an ID and regions. |
| `recommendation` | ID of one existing layout, used unless `--layout` overrides it. |
| `reference_jobs` | Assignments for actual selected images; empty when there are none. |
| `style` | Specific typography, color roles, line roles, and operator meanings. |
| `omit` | Deliberate omissions with their scientific source and reason; may be empty. |
| `review_focus` | One or more region-specific questions for checking the candidate. |

### Scientific brief binding

The brief is a JSON object with nonempty text `title`, `scientific_source`, and
`mechanism`; `must_show` is a nonempty text list and `must_not_show` is a text list
that may be empty. It is the scientific authority supplied to generation.

After checking that the design still matches the brief, obtain its digest with:

```sh
shasum -a 256 examples/design-brief.json
```

Copy the digest into `brief_sha256` when authoring or updating the plan. A digest
only binds file versions; it does not establish that a claim is true. Do not refresh
it to bypass a mismatch without reviewing the changed science and design.

### `method_graph`

`nodes` is a nonempty array of objects:

- `id`: unique node ID.
- `label`: exact short visible label.
- `source`: equation, section, or supplied scientific statement supporting this node.
- `emphasis`: `primary`, `support`, or `context`; respectively dominant, subordinate,
  or compact context in the drawing.
- `representation`: natural-language drawing instructions grounded in the node's
  meaning. Describe matrix shapes, alignment, grouping, or other visible structure
  directly. There is no fixed classification such as a mandatory matrix icon type.
  If a node appears at two scales, explain how its overview and detail differ.

`edges` is an array that may be empty. Each edge has unique `id`, existing node IDs
`from` and `to`, `kind` (`data`, `conditioning`, or `feedback`), `meaning` describing
the scientific relationship, and `source` supporting that relationship. Feedback
is drawn as a labeled return arrow distinct from forward data flow. The required
line-role fields cover data, conditioning, and zoom; no feedback style field is
required. Do not represent an enlarged view as a graph edge: it is not a scientific
transition or another execution of the operation.

### `layouts`

Each layout has:

- `id`: unique layout ID; `name`: short composition description.
- `reading_order`: nonempty ordered list of existing node IDs, without repetitions.
  It may contain only the main narrative path; context nodes can be omitted here.
- `regions`: nonempty array of region objects. Each has `id`, `purpose`, nonempty
  `node_ids`, `placement` in clear spatial language, and `scale_priority` of `large`,
  `medium`, or `small`. Region IDs are unique within a layout; different layouts can
  reuse region IDs so reference jobs and review questions remain applicable.
  Every node must appear in at least one region of every layout. Relative scale
  expresses visual priority, not measured scientific magnitude.
- `zoom_links`: array of overview/detail pairings; may be empty. Each object has
  `source_node`, `target_region`, `treatment: "paired-no-arrows"`, and `meaning`.
  The source node must appear both in the target region and in at least one other
  overview region. This establishes that the detail shows the same operation.
  The compiler requires the stated treatment, disallows duplicate pairs, and
  instructs the specified pairing lines without arrowheads or dataflow arrows between
  the two views. The assistant must ensure the descriptive line style agrees.
- `tradeoff`: what the composition gains or gives less space to.
- `reason_to_choose`: why this arrangement fits the reader question and use case.

All candidate layouts are structurally checked. Reference assignments and review
questions are then checked against the selected layout. If choosing another layout
makes their region IDs invalid, update those decisions rather than silently losing
their meaning. Only the selected layout enters the prompt.

### `reference_jobs`

Each job contains `reference_id` matching a real explicit `--reference-id`, a
nonempty `borrow` list of specific visual features, a `do_not_borrow` list that may
be empty, and nonempty `for_regions` listing regions in the selected layout.
Every actual input image needs at least one job; one reference may have several
jobs. Attachment order determines the image numbers used in the compiled prompt.

Name concrete features such as typography, paired framing, spatial organization,
or an explicitly checked mechanism. An image's text, labels, equations, or topology
do not supply unstated paper meaning. The compiler enforces identity and region
coverage; the assistant must inspect the image and judge scientific compatibility.

### `style`

- `profile`: `comic`, `roman`, or `modern`.
- `labels_font` and `math_font`: requested typefaces or precise typography instructions.
- `palette`: nonempty list of objects with `role`, `fill`, `stroke`, and `meaning`.
  Roles must be unique; fills and strokes are text, usually explicit hex colors.
  Each role must carry a clear consistent meaning. Different roles may use the same
  hex value; the validator does not invent or infer their scientific meaning.
- `line_roles`: object with text fields `data`, `conditioning`, and `zoom`. Declare
  distinguishable line treatments. Zoom describes pairing with no arrows and must
  not suggest a new computation. Natural-language style accuracy needs review.
- `text_policy`: concrete limits on label length, equations, captions, and density.
- `operator_legend`: array of objects with unique `symbol` and its `meaning`; may be
  empty. Only include operators justified by the scientific brief.

### Omissions and review

Each `omit` object has `item`, `reason`, and `source`. Record why excluding a real
detail improves this figure without changing its scientific account.

Each `review_focus` object has `region` naming a selected region and `question`
about a visible property that needs inspection, such as whether an overview/detail
pair looks like one operation or whether a color consistently denotes the same
quantity. These questions enter generation instructions; they are not recorded
as passed checks.

## What validation guarantees

Bad versions, stale brief bindings, invalid enum values, duplicate IDs, unknown
endpoints, uncovered nodes, inconsistent zoom pairs, unmatched image assignments,
invalid selected regions, and explicit style conflicts are rejected before an
output directory is created. This verifies usable instructions and their binding.
It does not verify whether the assistant understood the paper, whether the proposed
composition is good, or whether image generation obeyed it. Those judgments remain
part of reading the source, making the design, and reviewing the actual result.
