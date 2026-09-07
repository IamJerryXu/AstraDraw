# Editable scene v1

Single JSON source for component SVG/PPTX export and selected-object edits.
Top-level: `schema_version: 1`, `id`, `component` (descriptive identifier; the old demos use `ode`, `sde`, `flow-matching`),
`style` (`comic`, `roman`, `modern`), `width`, `height`, `scientific_notes` (strings),
`objects` (array). Coordinates are pixels, text boxes use top-left x/y.

Every object has a unique stable `id`, `type`, `role` and optionally `group`,
`locked` (boolean), `semantic_color` (boolean). Supported types:

- `text`: x, y, width, height, text, fontFamily, fontSize, fill, optional bold, italic.
- `rect` / `ellipse`: x, y, width, height, fill, stroke, strokeWidth, optional radius.
- `image`: x, y, width, height, `src` containing the original PNG or JPEG as a
  `data:image/png;base64,...` or `data:image/jpeg;base64,...` URI. No file paths,
  remote URLs, or network fetch are accepted. The frame contains the complete image,
  centered at its original aspect ratio (`fit: "contain"`, also the default).
  Optional `alt`, `src_sha256` (SHA-256 of decoded original bytes), and `provenance`
  (source/generation details) remain attached to the scene. A supplied digest must
  match. Export embeds a native PowerPoint picture and an SVG `<image>` with its
  data URI. Picture ID/name bindings and source metadata are retained in the map.
  Images may be moved through selection editing; color/text setters do not apply.
  Pictures remain raster assets, so diagram labels and connectors that must be
  editable must remain separate native objects. A full-page image cannot substitute
  for the required editable diagram. Native validation records pictures and shapes
  separately, and verifies each image maps to a real `pic` object.
- `polyline`: points (global [x,y] pairs), fill (`none` for open lines), stroke,
  strokeWidth, optional closed, dashed, dotted, endArrow. Colors may use RGBA for
  translucent regions. An explicitly modelled arrowhead is a separate object; do not
  also request an automatic head on the same arrow.
- A polyline can also have source, target (object IDs), source_anchor and
  target_anchor (`left`, `right`, `top`, `bottom`, `center`). Then endpoints refer
  to those anchors. Interior points describe a route, not extra semantic nodes.

Group is a membership label, not an additional shape. Scientific claims and
labels never change merely because a style changes. Sketch trajectories are
illustrative, not samples from an unspecified solver. Default edits preserve
all unselected objects except explicitly reported attached-connector endpoints.

Selection request: `scene_id`, `selected_ids`, `operations` (array), optional
`expected_sha256`. Supported initial operations: `move` with dx/dy and `set`
with properties from fill, stroke, strokeWidth, text, fontFamily, fontSize.
The edit operates on all selected IDs; no numeric PowerPoint ID is accepted
without an exported mapping. Screenshot selections require human/model grounding
to these IDs before executing. An empty or ambiguous selection must fail.

Initial implementation does not claim automatic two-way PowerPoint synchronization,
or automatic native PowerPoint connector attachment when users drag shapes in PPT.

The exporter supports repeated `--scene` inputs with matching canvas dimensions.
Its adjacent `.object-map.json` retains the array format and stores per-slide
`scene_sha256`, `source_scene_path`, and `pptx_sha256`, alongside object names and
actual file IDs. Session selection requires these fingerprints to match the current
scene and deck; an older map must not authorize an edit to a newer file.
