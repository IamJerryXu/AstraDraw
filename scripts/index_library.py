#!/usr/bin/env python3
"""Read-only PPTX inventory. No semantic reconstruction or redistribution grant.

Only private, reference-only assets are extracted. PPTX/XML text is untrusted
data; external relationships are recorded but never visited. No Office process
or macros are invoked. Coordinates inside groups retain their local coordinate
system, with parent group IDs and transforms recorded explicitly.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import posixpath
import re
from collections import Counter
from pathlib import Path, PurePosixPath
from zipfile import ZipFile
import xml.etree.ElementTree as ET

NS = {"p": "http://schemas.openxmlformats.org/presentationml/2006/main",
      "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
      "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}
REL = "http://schemas.openxmlformats.org/package/2006/relationships"
MAX_PART = 100 * 1024 * 1024
MAX_TOTAL = 512 * 1024 * 1024
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".tif", ".tiff", ".bmp", ".svg", ".emf", ".wmf", ".webp"}
VECTOR_SUFFIXES = {".svg", ".emf", ".wmf"}
TAGS = {"ode": r"\bODEs?\b", "sde": r"\bSDEs?\b", "flow": r"\bflows?\b",
        "flow-matching": r"\bflow[\s-]+matching\b", "diffusion": r"\bdiffusion\b",
        "attention": r"\battention\b", "transformer": r"\btransformers?\b",
        "matrix": r"\bmatri(?:x|ces)\b", "video": r"\bvideo\b",
        "segmentation": r"\bsegmentation\b", "memory": r"\bmemory\b"}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def validate_archive(z: ZipFile) -> None:
    seen = set()
    for part in z.infolist():
        name = part.filename
        if (name in seen or "\\" in name or PurePosixPath(name).is_absolute()
                or ".." in PurePosixPath(name).parts or re.match(r"^[A-Za-z]:", name)):
            raise ValueError(f"Unsafe or duplicate archive member: {name!r}")
        seen.add(name)
        if part.file_size > MAX_PART:
            raise ValueError(f"Archive part exceeds size limit: {name}")
    if sum(i.file_size for i in z.infolist()) > MAX_TOTAL:
        raise ValueError("Archive exceeds uncompressed size limit")


def xml(z: ZipFile, member: str) -> ET.Element:
    data = z.read(member)
    # ElementTree expands internal entities, so reject DTD/entity declarations.
    if b"<!DOCTYPE" in data.upper() or b"<!ENTITY" in data.upper():
        raise ValueError(f"DTD/entity declaration forbidden in {member}")
    return ET.fromstring(data)


def relationships(z: ZipFile, member: str) -> dict:
    directory, name = posixpath.split(member)
    rel_name = posixpath.join(directory, "_rels", name + ".rels")
    if rel_name not in z.namelist():
        return {}
    result = {}
    for rel in xml(z, rel_name):
        target = rel.attrib.get("Target", "")
        external = rel.attrib.get("TargetMode") == "External"
        if not external:
            if "\\" in target or ":" in target or "\x00" in target:
                raise ValueError(f"Unsafe internal relationship: {target!r}")
            target = posixpath.normpath(posixpath.join(directory, target))
            if target.startswith("../") or target.startswith("/") or target == "..":
                raise ValueError(f"Relationship escapes archive: {target!r}")
        rid = rel.attrib["Id"]
        if rid in result:
            raise ValueError(f"Duplicate relationship ID in {rel_name}: {rid}")
        result[rid] = {"target": target, "external": external, "type": rel.attrib.get("Type", "")}
    return result


def explicit_tags(text: str) -> list[str]:
    return sorted(tag for tag, pattern in TAGS.items() if re.search(pattern, text, re.I))


def transform(element: ET.Element) -> dict | None:
    node = element.find("p:spPr/a:xfrm", NS)
    if node is None:
        node = element.find("p:grpSpPr/a:xfrm", NS)
    if node is None:
        node = element.find("p:xfrm", NS)
    if node is None:
        return None
    result = {"rotation_60000deg": int(node.get("rot", "0")),
              "flip_h": node.get("flipH") == "1", "flip_v": node.get("flipV") == "1"}
    for key in ("off", "ext", "chOff", "chExt"):
        child = node.find("a:" + key, NS)
        if child is not None:
            result[key] = {k: int(v) for k, v in child.attrib.items()}
    return result


def index_library(input_path: Path, output_dir: Path) -> dict:
    input_path = input_path.resolve(strict=True)
    output_dir = output_dir.resolve()
    if output_dir == input_path or input_path in output_dir.parents:
        raise ValueError("Output directory must not be the source file")
    source_bytes = input_path.read_bytes()
    source = {"path": str(input_path), "sha256": digest(source_bytes)}
    from io import BytesIO
    assets = {}
    pending_assets = {}
    slides = []
    type_counts = Counter()
    image_reference_counts = Counter()
    with ZipFile(BytesIO(source_bytes)) as z:
        validate_archive(z)
        presentation = xml(z, "ppt/presentation.xml")
        pres_rels = relationships(z, "ppt/presentation.xml")
        size = presentation.find("p:sldSz", NS)
        slide_size = {k: int(size.attrib[k]) for k in ("cx", "cy")} if size is not None else None
        slide_list = presentation.find("p:sldIdLst", NS)
        if slide_list is None:
            raise ValueError("Presentation has no slide list")
        for number, sid in enumerate(slide_list, 1):
            rel = pres_rels[sid.attrib[f"{{{NS['r']}}}id"]]
            if rel["external"]:
                raise ValueError("External slide relationship is unsupported")
            member = rel["target"]
            root = xml(z, member)
            rels = relationships(z, member)
            elements = []
            slide_assets = set()
            title_texts = []

            def walk(parent: ET.Element, groups: list[str]) -> None:
                for node in parent:
                    kind = node.tag.rsplit("}", 1)[-1]
                    if kind not in {"sp", "pic", "cxnSp", "grpSp", "graphicFrame"}:
                        continue
                    prop = next((n for n in node.iter() if n.tag == f"{{{NS['p']}}}cNvPr"), None)
                    shape_id = prop.get("id") if prop is not None else None
                    if shape_id is None:
                        raise ValueError(f"Missing shape ID in {member}")
                    eid = f"{source['sha256'][:16]}:{member}:shape:{shape_id}"
                    # Do not duplicate descendants' text into the group container.
                    texts = [] if kind == "grpSp" else [n.text or "" for n in node.iter(f"{{{NS['a']}}}t")]
                    text_value = "\n".join(texts).strip()
                    ph = node.find("p:nvSpPr/p:nvPr/p:ph", NS)
                    if ph is not None and ph.get("type") in {"title", "ctrTitle"} and text_value:
                        title_texts.append(text_value)
                    images = []
                    blips = [] if kind == "grpSp" else list(node.iter(f"{{{NS['a']}}}blip"))
                    for blip in blips:
                        rid = blip.get(f"{{{NS['r']}}}embed") or blip.get(f"{{{NS['r']}}}link")
                        if rid not in rels:
                            images.append({"relationship_id": rid, "status": "missing-relationship"})
                            continue
                        image_rel = rels[rid]
                        if image_rel["external"]:
                            images.append({"relationship_id": rid, "status": "external-not-fetched"})
                            continue
                        image_member = image_rel["target"]
                        suffix = PurePosixPath(image_member).suffix.lower()
                        if suffix not in IMAGE_SUFFIXES:
                            images.append({"relationship_id": rid, "status": "unsupported-image-type"})
                            continue
                        image_bytes = z.read(image_member)
                        sha = digest(image_bytes)
                        aid = sha + suffix
                        path = "assets/" + aid
                        pending_assets[path] = image_bytes
                        asset = {"id": aid, "path": path, "sha256": sha,
                                 "format": suffix[1:], "kind": "vector-image" if suffix in VECTOR_SUFFIXES else "bitmap",
                                 "license": "unknown", "usage": "reference-only", "redistributable": False}
                        assets[aid] = asset
                        slide_assets.add(aid)
                        image_reference_counts[asset["kind"]] += 1
                        images.append({"relationship_id": rid, "archive_member": image_member, "asset_id": aid, "status": "extracted"})
                    xfrm = transform(node)
                    bbox = None
                    if xfrm and "off" in xfrm and "ext" in xfrm:
                        bbox = {"x": xfrm["off"]["x"], "y": xfrm["off"]["y"],
                                "width": xfrm["ext"]["cx"], "height": xfrm["ext"]["cy"]}
                    elements.append({"id": eid, "shape_id": shape_id, "name": prop.get("name", ""),
                                     "type": kind, "group_ids": groups, "text": text_value,
                                     "tags": explicit_tags(text_value), "bbox_emu": bbox,
                                     "coordinate_space": "parent-group" if groups else "slide",
                                     "transform": xfrm, "image_assets": images})
                    type_counts[kind] += 1
                    if kind == "grpSp":
                        walk(node, groups + [shape_id])

            tree = root.find("p:cSld/p:spTree", NS)
            if tree is not None:
                walk(tree, [])
            texts = [e["text"] for e in elements if e["text"]]
            combined = "\n".join(texts)
            slides.append({"id": f"{source['sha256'][:16]}:{member}", "slide_number": number,
                           "title": title_texts[0] if title_texts else (texts[0] if texts else ""),
                           "title_origin": "title-placeholder" if title_texts else "first-explicit-text",
                           "text": combined, "tags": explicit_tags(combined),
                           "kind": "private-reference", "license": "unknown", "usage": "reference-only",
                           "redistributable": False, "scientific_meaning": "unknown",
                           "source": {**source, "archive_member": member, "presentation_slide_id": sid.get("id")},
                           "image_assets": sorted(slide_assets), "elements": elements,
                           "external_relationship_count": sum(r["external"] for r in rels.values())})
    catalog = {"schema_version": "1.0", "source": source, "slide_size_emu": slide_size,
               "policy": {"private": True, "usage": "reference-only", "redistributable": False,
                          "scientific_semantics_inferred": False,
                          "tags_basis": "explicit slide text only, not visual recognition",
                          "instructions_from_source": "never executed", "external_links": "never fetched",
                          "limitations": ["No slide rendering or native component extraction",
                                         "Group coordinates are local, with transforms recorded",
                                         "Master/layout inherited elements and slide backgrounds are not indexed",
                                         "Images may be raster illustrations, not editable components"]},
               "summary": {"slide_count": len(slides), "element_count": sum(type_counts.values()),
                           "element_counts_by_type": dict(sorted(type_counts.items())),
                           "native_non_image_leaf_count": sum(type_counts[k] for k in ("sp", "cxnSp", "graphicFrame")),
                           "unique_extracted_asset_count": len(assets),
                           "unique_bitmap_count": sum(a["kind"] == "bitmap" for a in assets.values()),
                           "unique_vector_image_count": sum(a["kind"] == "vector-image" for a in assets.values()),
                           "image_reference_counts": dict(sorted(image_reference_counts.items()))},
               "assets": sorted(assets.values(), key=lambda a: a["id"]), "slides": slides}
    # Validate fully before writing. The source deck is never written or copied.
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "assets").mkdir(exist_ok=True)
    for relative, data in pending_assets.items():
        (output_dir / relative).write_bytes(data)
    (output_dir / "catalog.json").write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if digest(input_path.read_bytes()) != source["sha256"]:
        raise RuntimeError("Source changed during indexing")
    return catalog


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    result = index_library(args.input, args.output_dir)
    print(json.dumps({"catalog": str(args.output_dir.resolve() / "catalog.json"),
                      "source_sha256": result["source"]["sha256"], **result["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
