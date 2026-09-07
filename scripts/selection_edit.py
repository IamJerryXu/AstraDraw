#!/usr/bin/env python3
"""Conservative scene edits; never edits PPTX files or overwrites a source.

Request operations use ``op: move`` (dx/dy) or ``op: set`` (properties).
Changing fill/stroke of semantic_color objects requires the explicit request
flag ``allow_semantic_color: true`` and is marked for scientific review.
"""
from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import json
import math
import os
import re
from pathlib import Path
import tempfile


class EditError(ValueError):
    pass


SETTERS = {"fill", "stroke", "strokeWidth", "text", "fontFamily", "fontSize"}
TYPE_SETTERS = {
    "text": {"fill", "text", "fontFamily", "fontSize"},
    "rect": {"fill", "stroke", "strokeWidth"},
    "ellipse": {"fill", "stroke", "strokeWidth"},
    "polyline": {"fill", "stroke", "strokeWidth"},
    "image": set(),
}
ANCHORS = {"left", "right", "top", "bottom", "center"}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def object_hash(obj):
    return digest(json.dumps(obj, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=False, allow_nan=False).encode())


def number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise EditError(f"{name} must be a finite number")
    try:
        finite = math.isfinite(value)
    except OverflowError:
        finite = False
    if not finite:
        raise EditError(f"{name} must be a finite number")
    return value


def validate_scene(scene):
    if (not isinstance(scene, dict) or type(scene.get("schema_version")) is not int
            or scene.get("schema_version") != 1):
        raise EditError("Expected scene schema_version 1")
    if not isinstance(scene.get("id"), str) or not scene["id"]:
        raise EditError("Scene needs a nonempty id")
    for field in ("width", "height"):
        if number(scene.get(field), field) <= 0:
            raise EditError(f"{field} must be positive")
    objects = scene.get("objects")
    if not isinstance(objects, list):
        raise EditError("objects must be an array")
    lookup = {}
    for obj in objects:
        if not isinstance(obj, dict):
            raise EditError("Every object must be an object")
        ident = obj.get("id")
        if not isinstance(ident, str) or not ident or ident in lookup:
            raise EditError("Missing or ambiguous object ID")
        lookup[ident] = obj
        kind = obj.get("type")
        if not isinstance(kind, str) or kind not in TYPE_SETTERS:
            raise EditError(f"Unsupported object type: {kind}")
        if kind == 'image':
            match = re.fullmatch(r'data:(image/(?:png|jpeg));base64,([A-Za-z0-9+/]+={0,2})', obj.get('src', '') if isinstance(obj.get('src'),str) else '')
            if not match:
                raise EditError('Image src must be an embedded PNG/JPEG data URI')
            try:
                data = base64.b64decode(match[2], validate=True)
            except ValueError as exc:
                raise EditError('Invalid image base64') from exc
            if base64.b64encode(data).decode() != match[2] or not (
                data.startswith(b'\x89PNG\r\n\x1a\n') if match[1] == 'image/png'
                else data.startswith(b'\xff\xd8') and data.endswith(b'\xff\xd9')):
                raise EditError('Invalid image bytes')
            if 'src_sha256' in obj and obj['src_sha256'] != digest(data):
                raise EditError('Image source hash mismatch')
            if obj.get('fit', 'contain') != 'contain':
                raise EditError('Image fit must preserve the complete source')
        for flag in ("locked", "semantic_color"):
            if flag in obj and not isinstance(obj[flag], bool):
                raise EditError(f"{ident}.{flag} must be boolean")
        if kind == "polyline":
            points = obj.get("points")
            if not isinstance(points, list) or len(points) < 2:
                raise EditError(f"{ident} needs at least two points")
            for point in points:
                if not isinstance(point, list) or len(point) != 2:
                    raise EditError("Each point must contain x and y")
                for coordinate in point:
                    number(coordinate, ident + ".points")
        else:
            for field in ("x", "y", "width", "height"):
                number(obj.get(field), ident + "." + field)
            if obj["width"] <= 0 or obj["height"] <= 0:
                raise EditError(f"{ident} dimensions must be positive")
        for field in ("fontSize", "strokeWidth"):
            if field in obj:
                value = number(obj[field], ident + "." + field)
                if value < 0 or (field == "fontSize" and value == 0):
                    raise EditError(f"Invalid {field}")
    for obj in objects:
        if obj["type"] != "polyline":
            continue
        for side in ("source", "target"):
            if side in obj:
                if (not isinstance(obj[side], str) or obj[side] not in lookup
                        or lookup[obj[side]]["type"] == "polyline"):
                    raise EditError(f"{obj['id']} has an invalid {side}")
                endpoint_anchor = obj.get(side + "_anchor", "center")
                if not isinstance(endpoint_anchor, str) or endpoint_anchor not in ANCHORS:
                    raise EditError("Unsupported endpoint anchor")
    return lookup


def anchor(obj, side):
    x, y, w, h = (obj[k] for k in ("x", "y", "width", "height"))
    return {"left": [x, y + h / 2], "right": [x + w, y + h / 2],
            "top": [x + w / 2, y], "bottom": [x + w / 2, y + h],
            "center": [x + w / 2, y + h / 2]}[side]


def check_bounds(obj, width, height):
    points = obj["points"] if obj["type"] == "polyline" else [
        [obj["x"], obj["y"]], [obj["x"] + obj["width"], obj["y"] + obj["height"]]]
    if any(not (0 <= x <= width and 0 <= y <= height) for x, y in points):
        raise EditError(f"{obj['id']} would be outside canvas bounds")


def apply_request(scene, request, source_sha256=None):
    """Return an independent edited scene and audit; mutate neither argument."""
    before = validate_scene(scene)
    if not isinstance(request, dict) or request.get("scene_id") != scene["id"]:
        raise EditError("scene_id does not match")
    expected = request.get("expected_sha256")
    if expected is not None and (not isinstance(expected, str) or expected != source_sha256):
        raise EditError("Stale scene: expected_sha256 does not match source bytes")
    ids = request.get("selected_ids")
    if (not isinstance(ids, list) or not ids or
            any(not isinstance(i, str) for i in ids) or len(ids) != len(set(ids))):
        raise EditError("selected_ids must be nonempty and unique")
    if any(i not in before for i in ids):
        raise EditError("A selected ID does not exist")
    if any(before[i].get("locked") for i in ids):
        raise EditError("Selection contains a locked object")
    operations = request.get("operations")
    if not isinstance(operations, list) or not operations:
        raise EditError("operations must be nonempty")
    allow_semantic = request.get("allow_semantic_color", False)
    if not isinstance(allow_semantic, bool):
        raise EditError("allow_semantic_color must be boolean")
    result = copy.deepcopy(scene)
    after = {obj["id"]: obj for obj in result["objects"]}
    review_reasons = []
    for operation in operations:
        if not isinstance(operation, dict):
            raise EditError("Invalid operation")
        op = operation.get("op")
        if op == "move":
            if set(operation) != {"op", "dx", "dy"}:
                raise EditError("move supports only op, dx, dy")
            dx, dy = number(operation["dx"], "dx"), number(operation["dy"], "dy")
            for ident in ids:
                obj = after[ident]
                if obj["type"] == "polyline":
                    obj["points"] = [[x + dx, y + dy] for x, y in obj["points"]]
                else:
                    obj["x"] += dx
                    obj["y"] += dy
        elif op == "set":
            if set(operation) != {"op", "properties"}:
                raise EditError("set supports only op and properties")
            properties = operation["properties"]
            if not isinstance(properties, dict) or not properties or not set(properties) <= SETTERS:
                raise EditError("Unsupported or empty set properties")
            for key, value in properties.items():
                if key in ("fontSize", "strokeWidth"):
                    number(value, key)
                    if value < 0 or (key == "fontSize" and value == 0):
                        raise EditError(f"Invalid {key}")
                elif not isinstance(value, str) or (key != "text" and not value.strip()):
                    raise EditError(f"{key} must be a string")
            for ident in ids:
                obj = after[ident]
                if not set(properties) <= TYPE_SETTERS[obj["type"]]:
                    raise EditError(f"Properties do not apply to {ident}'s type")
                semantic_change = obj.get("semantic_color") and any(
                    key in properties and properties[key] != obj.get(key) for key in ("fill", "stroke"))
                if semantic_change:
                    if not allow_semantic:
                        raise EditError("Semantic color change requires allow_semantic_color=true")
                    review_reasons.append(f"Semantic color changed: {ident}")
                if "text" in properties and properties["text"] != obj.get("text"):
                    review_reasons.append(f"User-requested text changed: {ident}")
                obj.update(properties)
        else:
            raise EditError(f"Unsupported operation: {op}")
    moved_nodes = {ident for ident in ids if after[ident]["type"] != "polyline" and
                   any(before[ident][key] != after[ident][key] for key in ("x", "y"))}
    related = []
    for obj in result["objects"]:
        if obj["type"] != "polyline":
            continue
        for side, index in (("source", 0), ("target", -1)):
            if obj.get(side) in moved_nodes:
                point = anchor(after[obj[side]], obj.get(side + "_anchor", "center"))
                if obj["points"][index] != point:
                    if obj.get("locked"):
                        raise EditError(f"Attached connector {obj['id']} is locked")
                    related.append({"id": obj["id"], "endpoint": side,
                                    "attached_to": obj[side],
                                    "before": list(obj["points"][index]), "after": point})
                    obj["points"][index] = point
    validate_scene(result)
    changed = [ident for ident in before if before[ident] != after[ident]]
    related_ids = {item["id"] for item in related}
    for ident in set(ids) | related_ids:
        check_bounds(after[ident], result["width"], result["height"])
    for ident in set(before) - set(ids):
        allowed = copy.deepcopy(before[ident])
        if ident in related_ids:
            for item in related:
                if item["id"] == ident:
                    allowed["points"][0 if item["endpoint"] == "source" else -1] = item["after"]
        if allowed != after[ident]:
            raise EditError(f"Unexpected unselected change: {ident}")
    audit = {"schema_version": 1, "scene_id": scene["id"],
             "source_sha256": source_sha256, "selected_ids": ids,
             "changed_ids": changed, "related_endpoints": related,
             "interior_routes_preserved_for_unselected": True,
             "no_unselected_drift": True,
             "scientific_review_required": bool(review_reasons),
             "scientific_review_reasons": list(dict.fromkeys(review_reasons)),
             "object_hashes": {ident: {"before": object_hash(before[ident]),
                                        "after": object_hash(after[ident])} for ident in before},
             "limitations": ["Canvas check uses object boxes, not rendered glyph extents.",
                             "No PowerPoint GUI integration or two-way synchronization."]}
    return result, audit


def parse_json(data):
    def reject_duplicates(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise EditError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result
    return json.loads(data, object_pairs_hook=reject_duplicates)


def write_exclusive_pair(output, content, audit_path, audit_content):
    """Publish complete files without replacement; roll back our file on failure."""
    if output.exists() or audit_path.exists() or output.is_symlink() or audit_path.is_symlink():
        raise EditError("Output or audit already exists; choose a new output path")
    staged, published = [], []
    try:
        for destination, payload in ((output, content), (audit_path, audit_content)):
            with tempfile.NamedTemporaryFile(dir=destination.parent, prefix=".selection-", delete=False) as tmp:
                staged.append(Path(tmp.name))
                tmp.write(payload)
                tmp.flush()
                os.fsync(tmp.fileno())
            os.link(tmp.name, destination)
            published.append((destination, Path(tmp.name)))
    except BaseException:
        for destination, source in published:
            if destination.exists() and os.path.samestat(destination.stat(), source.stat()):
                destination.unlink()
        raise
    finally:
        for path in staged:
            path.unlink(missing_ok=True)


def edit_files(scene_path, request_path, output_path):
    scene_path, request_path, output = map(Path, (scene_path, request_path, output_path))
    audit_path = output.with_suffix(".audit.json")
    if output.resolve() in (scene_path.resolve(), request_path.resolve()) or audit_path.resolve() in (
            scene_path.resolve(), request_path.resolve(), output.resolve()):
        raise EditError("Input, output and audit paths must be distinct")
    source_bytes = scene_path.read_bytes()
    result, audit = apply_request(parse_json(source_bytes), parse_json(request_path.read_bytes()), digest(source_bytes))
    content = (json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode()
    audit.update({"output_sha256": digest(content), "source_path": str(scene_path.resolve()),
                  "output_path": str(output.resolve()),
                  "reversal": "The original source is unchanged; use it to restore the previous scene."})
    audit_content = (json.dumps(audit, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode()
    write_exclusive_pair(output, content, audit_path, audit_content)
    return audit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scene", type=Path, required=True)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        audit = edit_files(args.scene, args.request, args.output)
    except (EditError, OSError, json.JSONDecodeError) as exc:
        parser.exit(2, f"Selection edit rejected: {exc}\n")
    print(json.dumps({"output": str(args.output), "changed_ids": audit["changed_ids"],
                      "scientific_review_required": audit["scientific_review_required"]}))


if __name__ == "__main__":
    main()
