#!/usr/bin/env python3
"""Versioned local reference records. Registration never grants upload/publication rights."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
STATUSES = ("candidate", "user-approved", "rejected")
ROLES = ("style", "mechanism", "asset")
UNKNOWN_LICENSES = ("unknown", "unspecified", "unverified", "")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def contained(root, value):
    root = Path(root).resolve()
    path = (root / value).resolve()
    if not path.is_relative_to(root):
        raise ValueError("Reference path escapes the project")
    return path


def local_path(root, value):
    path = contained(root, value)
    if not path.is_relative_to((Path(root).resolve() / ".local")):
        raise ValueError("Private or unknown-license references must remain under .local/")
    return path


def record_path(root, reference_id):
    if not isinstance(reference_id, str) or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]{0,119}", reference_id):
        raise ValueError("Reference id must be 1–120 letters, digits, dots, underscores or hyphens")
    return local_path(root, f".local/references/{reference_id}.json")


def restricted(record):
    return record["private"] or record["license"].strip().lower() in UNKNOWN_LICENSES


def validate_metadata(record, root=ROOT):
    """Validate record identity without requiring historical image bytes to survive."""
    if not isinstance(record, dict) or record.get("version") != 1:
        raise ValueError("Invalid reference record")
    record_path(root, record.get("id"))
    for key in ("path", "license", "title", "sha256"):
        if not isinstance(record.get(key), str) or not record[key].strip():
            raise ValueError(f"Invalid reference field: {key}")
    if type(record.get("private")) is not bool:
        raise ValueError("Reference private field must be a boolean")
    if record.get("aesthetic_status") not in STATUSES or record.get("role") not in ROLES:
        raise ValueError("Invalid reference aesthetic status or role")
    if not isinstance(record.get("approval_evidence"), str):
        raise ValueError("Approval evidence must be text")
    if record["aesthetic_status"] == "user-approved" and not record["approval_evidence"].strip():
        raise ValueError("User-approved references require explicit approval evidence")
    if not isinstance(record.get("tags"), list) or any(not isinstance(x, str) for x in record["tags"]):
        raise ValueError("Reference tags must be text lists")
    if Path(record["path"]).is_absolute() or ".." in Path(record["path"]).parts:
        raise ValueError("Reference path must be project-relative without traversal")
    if record.get("supersedes"):
        record_path(root, record["supersedes"])
    return record


def validate(record, root=ROOT):
    validate_metadata(record, root)
    path = local_path(root, record["path"]) if restricted(record) else contained(root, record["path"])
    if not path.is_file():
        raise ValueError("Registered reference image is missing")
    if digest(path) != record["sha256"]:
        raise ValueError("Registered reference hash mismatch; register a new version")
    # Require a real supported raster attachment, not a filename referring to SVG/PPTX.
    with path.open("rb") as stream:
        header = stream.read(12)
    if not (header.startswith(b"\x89PNG\r\n\x1a\n") or header.startswith(b"\xff\xd8\xff")
            or (header.startswith(b"RIFF") and header[8:12] == b"WEBP")):
        raise ValueError("Register a PNG, JPEG or WebP raster reference")
    return path


def register(reference_id, path, *, role="style", license="unknown", private=False,
             aesthetic_status="candidate", approval_evidence="", title=None, tags=(),
             style=None, supersedes=None, root=ROOT):
    root = Path(root).resolve()
    destination = record_path(root, reference_id)
    if destination.exists():
        raise ValueError("Reference id already exists; choose a new version id")
    image = contained(root, path)
    record = {"version": 1, "id": reference_id, "path": str(image.relative_to(root)),
              "sha256": digest(image), "role": role, "license": license, "private": private,
              "aesthetic_status": aesthetic_status, "approval_evidence": approval_evidence,
              "title": title or reference_id, "tags": list(tags), "style": style,
              "created_at": datetime.now(timezone.utc).isoformat(),
              "publication_authorized": False, "upload_authorized": False,
              "usage": "reference-only"}
    if supersedes:
        load_metadata(supersedes, root=root)
        record["supersedes"] = supersedes
    validate(record, root)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    return record


def load_metadata(reference_id, root=ROOT):
    record = json.loads(record_path(root, reference_id).read_text(encoding="utf-8"))
    validate_metadata(record, root)
    if record.get("id") != reference_id:
        raise ValueError("Reference id does not match its record filename")
    return record


def load(reference_id, root=ROOT):
    record = load_metadata(reference_id, root)
    validate(record, root)
    return record


def active_metadata(root=ROOT):
    """Ignore legacy/non-registry records; determine versions before checking images."""
    directory = local_path(root, ".local/references")
    if not directory.exists():
        return []
    records = []
    for path in sorted(directory.glob("*.json")):
        try:
            records.append(load_metadata(path.stem, root=root))
        except (ValueError, OSError, KeyError, TypeError):
            # Old local reference notes are a different format and remain untouched.
            # A malformed/unrelated record must not disable other valid references.
            continue
    superseded = {r["supersedes"] for r in records if r.get("supersedes")}
    return [r for r in records if r["id"] not in superseded]


def list_references(root=ROOT, include_private=False):
    results = []
    for record in active_metadata(root):
        if restricted(record) and not include_private:
            continue
        try:
            validate(record, root)
        except (ValueError, OSError):
            # Discovery lists usable assets. Explicit selection below reports damage.
            continue
        results.append(record)
    return results


def selected(reference_ids, *, allow_private=False, allow_candidates=False, root=ROOT):
    if len(set(reference_ids)) != len(reference_ids) or len(reference_ids) > 5:
        raise ValueError("Choose at most five distinct registered references")
    records = []
    active_ids = {r["id"] for r in active_metadata(root)} if reference_ids else set()
    for reference_id in reference_ids:
        record = load_metadata(reference_id, root=root)
        if reference_id not in active_ids:
            raise ValueError(f"Reference {reference_id} is superseded; select its new version")
        if record["aesthetic_status"] == "rejected" or (record["aesthetic_status"] == "candidate" and not allow_candidates):
            raise ValueError(f"Reference {reference_id} is {record['aesthetic_status']}; only user-approved references can prepare generation input")
        if restricted(record) and not allow_private:
            raise ValueError("Private or unknown-license references require explicit --allow-private")
        validate(record, root)
        records.append(record)
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    subs = parser.add_subparsers(dest="command", required=True)
    add = subs.add_parser("register")
    add.add_argument("--id", required=True)
    add.add_argument("--path", type=Path, required=True)
    add.add_argument("--role", choices=ROLES, default="style")
    add.add_argument("--license", default="unknown")
    add.add_argument("--private", action="store_true")
    add.add_argument("--status", choices=STATUSES, default="candidate")
    add.add_argument("--approval-evidence", default="")
    add.add_argument("--title")
    add.add_argument("--tag", action="append", default=[])
    add.add_argument("--style")
    add.add_argument("--supersedes")
    listing = subs.add_parser("list")
    listing.add_argument("--include-private", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "register":
            result = register(args.id, args.path, role=args.role, license=args.license,
                              private=args.private, aesthetic_status=args.status,
                              approval_evidence=args.approval_evidence, title=args.title,
                              tags=args.tag, style=args.style, supersedes=args.supersedes, root=args.root)
        else:
            result = list_references(root=args.root, include_private=args.include_private)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.exit(2, f"Error: {error}\n")


if __name__ == "__main__":
    main()
