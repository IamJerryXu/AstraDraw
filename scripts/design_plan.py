"""Validate assistant-authored design decisions and compile them for image generation.

This module checks structure and provenance; it does not infer a method or judge
scientific correctness from a paper. The assistant supplies those judgments.
"""
import hashlib
import json
from pathlib import Path


def _object(value, where):
    if not isinstance(value, dict):
        raise ValueError(f"Design plan {where} must be an object")
    return value


def _text(value, where):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Design plan {where} must be nonempty text")
    return value


def _list(value, where, nonempty=False):
    if not isinstance(value, list) or (nonempty and not value):
        raise ValueError(f"Design plan {where} must be {'a nonempty' if nonempty else 'a'} list")
    return value


def _texts(value, where, nonempty=False):
    for entry in _list(value, where, nonempty):
        _text(entry, where)
    return value


def _fields(value, fields, where):
    _object(value, where)
    for field in fields:
        _text(value.get(field), f"{where}.{field}")


def _choice(value, choices, where):
    if not isinstance(value, str) or value not in choices:
        raise ValueError(f"Design plan {where} must be one of: {', '.join(choices)}")


def _indexed(values, where, nonempty=True, key="id"):
    result = {}
    for entry in _list(values, where, nonempty):
        _object(entry, where)
        identity = _text(entry.get(key), f"{where}.{key}")
        if identity in result:
            raise ValueError(f"Design plan duplicate {where} {key}: {identity}")
        result[identity] = entry
    return result


def _members(values, allowed, where, nonempty=True):
    _texts(values, where, nonempty)
    if len(set(values)) != len(values):
        raise ValueError(f"Design plan duplicate IDs in {where}")
    unknown = set(values) - set(allowed)
    if unknown:
        raise ValueError(f"Design plan unknown IDs in {where}: {', '.join(sorted(unknown))}")


def validate(plan, brief_sha256, reference_ids, layout_id=None, style=None,
             actual_reference_ids=None):
    """Return the selected layout after checking all plans and selected bindings.

    Region IDs are unique within each layout. Alternative layouts may reuse IDs
    so the same reference jobs can apply, but selected jobs must resolve exactly.
    """
    _object(plan, "root")
    if type(plan.get("version")) is not int or plan["version"] != 1:
        raise ValueError("Design plan version must be 1")
    _fields(plan, ("reader_question", "main_message", "brief_sha256", "recommendation"), "root")
    if plan["brief_sha256"] != brief_sha256:
        raise ValueError("Design plan brief_sha256 is stale or does not match the scientific brief")
    graph = _object(plan.get("method_graph"), "method_graph")
    nodes = _indexed(graph.get("nodes"), "nodes")
    for node in nodes.values():
        _fields(node, ("label", "source", "representation"), f"node {node['id']}")
        _choice(node.get("emphasis"), ("primary", "support", "context"), "node emphasis")
    edges = _indexed(graph.get("edges"), "edges", nonempty=False)
    for edge in edges.values():
        _fields(edge, ("from", "to", "meaning", "source"), f"edge {edge['id']}")
        if edge["from"] not in nodes or edge["to"] not in nodes:
            raise ValueError(f"Design plan edge {edge['id']} has an unknown endpoint")
        _choice(edge.get("kind"), ("data", "conditioning", "feedback"), "edge kind")
    layouts = _indexed(plan.get("layouts"), "layouts")
    if plan["recommendation"] not in layouts:
        raise ValueError("Design plan recommendation names an unknown layout")
    selected_id = layout_id if layout_id is not None else plan["recommendation"]
    _text(selected_id, "selected layout")
    if selected_id not in layouts:
        raise ValueError(f"Design plan unknown selected layout: {selected_id}")
    for layout in layouts.values():
        _fields(layout, ("name", "tradeoff", "reason_to_choose"), f"layout {layout['id']}")
        _members(layout.get("reading_order"), nodes, "reading_order")
        regions = _indexed(layout.get("regions"), "regions")
        covered = set()
        for region in regions.values():
            _fields(region, ("purpose", "placement"), f"region {region['id']}")
            _choice(region.get("scale_priority"), ("large", "medium", "small"), "region scale_priority")
            _members(region.get("node_ids"), nodes, f"region {region['id']} node_ids")
            covered.update(region["node_ids"])
        if covered != set(nodes):
            raise ValueError(f"Design plan layout {layout['id']} has nodes with no region: "
                             + ", ".join(sorted(set(nodes) - covered)))
        zoom_pairs = set()
        for zoom in _list(layout.get("zoom_links"), "zoom_links"):
            _fields(zoom, ("source_node", "target_region", "meaning"), "zoom link")
            _choice(zoom.get("treatment"), ("paired-no-arrows",), "zoom treatment")
            source, target = zoom["source_node"], zoom["target_region"]
            if source not in nodes or target not in regions:
                raise ValueError("Design plan zoom link names an unknown node or region")
            if source not in regions[target]["node_ids"]:
                raise ValueError("Design plan zoom target must contain the same source node")
            if not any(source in region["node_ids"] for rid, region in regions.items() if rid != target):
                raise ValueError("Design plan zoom source must also appear in a non-target overview region")
            pair = (source, target)
            if pair in zoom_pairs:
                raise ValueError("Design plan duplicate zoom link")
            zoom_pairs.add(pair)
    selected = layouts[selected_id]
    regions = {region["id"]: region for region in selected["regions"]}
    selected_refs = set(reference_ids)
    actual_refs = set(reference_ids if actual_reference_ids is None else actual_reference_ids)
    jobs = _list(plan.get("reference_jobs"), "reference_jobs", nonempty=bool(actual_refs))
    assigned = set()
    for job in jobs:
        _fields(job, ("reference_id",), "reference job")
        if job["reference_id"] not in selected_refs or job["reference_id"] not in actual_refs:
            raise ValueError("Design plan reference job must match an actual selected reference-id")
        _texts(job.get("borrow"), "reference borrow", nonempty=True)
        _texts(job.get("do_not_borrow"), "reference do_not_borrow")
        _members(job.get("for_regions"), regions, "reference for_regions")
        assigned.add(job["reference_id"])
    if assigned != actual_refs:
        raise ValueError("Design plan needs a reference job for every actual input image: "
                         + ", ".join(sorted(actual_refs - assigned)))
    visual = _object(plan.get("style"), "style")
    _choice(visual.get("profile"), ("comic", "roman", "modern"), "style profile")
    if style is not None and style != visual["profile"]:
        raise ValueError("CLI style conflicts with design plan style profile")
    _fields(visual, ("labels_font", "math_font", "text_policy"), "style")
    for color in _indexed(visual.get("palette"), "palette", key="role").values():
        _fields(color, ("fill", "stroke", "meaning"), "palette")
    _fields(visual.get("line_roles"), ("data", "conditioning", "zoom"), "line_roles")
    for operator in _indexed(visual.get("operator_legend"), "operator_legend", nonempty=False, key="symbol").values():
        _fields(operator, ("meaning",), "operator legend")
    for omission in _list(plan.get("omit"), "omit"):
        _fields(omission, ("item", "reason", "source"), "omit")
    for focus in _list(plan.get("review_focus"), "review_focus", nonempty=True):
        _fields(focus, ("region", "question"), "review focus")
        if focus["region"] not in regions:
            raise ValueError("Design plan review_focus names an unknown selected region")
    return selected


def compile_prompt(plan, layout, actual_reference_ids):
    """Translate validated decisions into concrete drawing instructions, not JSON."""
    nodes = {node["id"]: node for node in plan["method_graph"]["nodes"]}
    labels = lambda ids: ", ".join(f'“{nodes[nid]["label"]}” [{nid}]' for nid in ids)
    lines = ["DESIGN DECISIONS (assistant-authored from the scientific brief):",
             f"Answer this reader question visually: {plan['reader_question']}",
             f"The single main message must be: {plan['main_message']}",
             f"Use layout {layout['id']} — {layout['name']}.",
             "Guide the eye through: " + " → ".join(nodes[nid]["label"] for nid in layout["reading_order"]) + ".",
             f"Why this composition: {layout['reason_to_choose']}",
             f"Its deliberate tradeoff: {layout['tradeoff']}",
             "Arrange the following regions with the stated relative space and placement:"]
    for region in layout["regions"]:
        lines.append(f"Region {region['id']}: {region['purpose']}. Place it {region['placement']}; "
                     f"give it {region['scale_priority']} relative visual space. Include {labels(region['node_ids'])}.")
    emphasis = {"primary": "make this a dominant focal element", "support": "keep this legible but subordinate",
                "context": "show this compactly as context"}
    lines.append("Draw the method elements as follows; preserve the quoted labels:")
    for node in nodes.values():
        lines.append(f"“{node['label']}” [{node['id']}]: {node['representation']}; {emphasis[node['emphasis']]}. "
                     f"Scientific grounding: {node['source']}.")
    visual = plan["style"]
    lines.append("Only the following scientific connections are specified. Do not add arrows between regions merely because they are adjacent:")
    for edge in plan["method_graph"]["edges"]:
        treatment = (visual["line_roles"][edge["kind"]] if edge["kind"] in ("data", "conditioning") else
                     "a clearly labeled feedback return arrow, visually distinct from forward data flow")
        lines.append(f"{edge['kind'].capitalize()} connection [{edge['id']}]: “{nodes[edge['from']]['label']}” "
                     f"→ “{nodes[edge['to']]['label']}” means {edge['meaning']}. Draw with {treatment}. "
                     f"Scientific grounding: {edge['source']}.")
    if not plan["method_graph"]["edges"]:
        lines.append("No scientific arrows are specified; use the reading order and spatial arrangement without inventing flow.")
    for zoom in layout["zoom_links"]:
        origins = [r["id"] for r in layout["regions"] if r["id"] != zoom["target_region"] and zoom["source_node"] in r["node_ids"]]
        lines.append(f"Overview/detail pair: “{nodes[zoom['source_node']]['label']}” in {', '.join(origins)} "
                     f"is the SAME operation expanded in region {zoom['target_region']}: {zoom['meaning']}. "
                     f"Pair the views with {visual['line_roles']['zoom']}; NO arrowheads or dataflow arrows between the paired views. "
                     "Do not depict a second processing stage or a second execution of the operation.")
    lines.extend(["The following specific visual grammar takes precedence over generic font and palette examples above; keep its exact assignments:",
                  f"Profile: {visual['profile']}. Labels: {visual['labels_font']}. Mathematics: {visual['math_font']}.",
                  f"Text policy: {visual['text_policy']}",
                  f"Line grammar: data uses {visual['line_roles']['data']}; conditioning uses {visual['line_roles']['conditioning']}; "
                  f"overview/detail pairing uses {visual['line_roles']['zoom']}, always without arrows. "
                  "Apply these treatments only to the corresponding declared relationships."])
    for color in visual["palette"]:
        lines.append(f"Color role “{color['role']}”: fill {color['fill']}, stroke {color['stroke']}; "
                     f"this denotes {color['meaning']}. Keep this role consistent across regions.")
    for operator in visual["operator_legend"]:
        lines.append(f"Operator “{operator['symbol']}” means {operator['meaning']}; use only with that meaning.")
    lines.append("Reference borrowing assignments (image numbers match the actual attachments):" if actual_reference_ids else
                 "No reference images are selected; the composition is original to this design plan.")
    image_numbers = {rid: i for i, rid in enumerate(actual_reference_ids, 1)}
    for job in plan["reference_jobs"]:
        lines.append(f"Image {image_numbers[job['reference_id']]} [{job['reference_id']}] informs regions "
                     f"{', '.join(job['for_regions'])}. Borrow: {'; '.join(job['borrow'])}. "
                     f"Do not borrow: {'; '.join(job['do_not_borrow']) or 'any unassigned content'}.")
    lines.append("No reference supplies an unstated scientific meaning, mechanism, label, equation or result. "
                 "Use the scientific brief and the explicitly grounded method elements as authority.")
    for omission in plan["omit"]:
        lines.append(f"Omit {omission['item']} because {omission['reason']}. Grounding: {omission['source']}.")
    lines.append("Design review questions to preserve in the candidate:")
    for focus in plan["review_focus"]:
        lines.append(f"Region {focus['region']}: {focus['question']}")
    lines.append("END DESIGN DECISIONS")
    return "\n".join(lines) + "\n"


def load_and_compile(path, brief_sha256, reference_ids, layout_id=None, style=None,
                     actual_reference_ids=None):
    raw = Path(path).read_bytes()
    plan = json.loads(raw)
    layout = validate(plan, brief_sha256, reference_ids, layout_id, style, actual_reference_ids)
    actual = list(reference_ids if actual_reference_ids is None else actual_reference_ids)
    return {"prompt": compile_prompt(plan, layout, actual), "sha256": hashlib.sha256(raw).hexdigest(),
            "layout_id": layout["id"], "style": plan["style"]["profile"]}
