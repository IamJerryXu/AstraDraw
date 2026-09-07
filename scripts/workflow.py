#!/usr/bin/env python3
"""Versioned local figure sessions, explicit review, and grounded selection edits.

This is a state/evidence helper for the agent workflow, not a model runner.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import zipfile
import xml.etree.ElementTree as ET

from afw import inspect_pptx
from selection_edit import apply_request, validate_scene

ROOT = Path(__file__).resolve().parents[1]
ROLES = ('source', 'reference', 'candidate', 'scene', 'pptx', 'preview', 'report')
CHECKS = ('scientific', 'visual', 'selection')


def now():
    return datetime.now(timezone.utc).isoformat()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def valid_id(value):
    if not isinstance(value, str) or not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_.-]{0,79}', value):
        raise ValueError('Use a short identifier containing letters, digits, hyphens or underscores')
    return value


def local_run(run, root=ROOT):
    run = Path(run).resolve()
    if not run.is_relative_to((root / '.local').resolve()) or run == (root / '.local').resolve():
        raise ValueError('Figure sessions must remain in a subdirectory of .local/')
    return run


def write_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')


def load(run):
    files = sorted((Path(run) / 'history').glob('[0-9][0-9][0-9][0-9][0-9][0-9].json'))
    if not files:
        raise ValueError('Session not initialized')
    state = read(files[-1])
    if state.get('schema_version') != 1:
        raise ValueError('Unsupported session version')
    return state


@contextmanager
def lock(run):
    path = Path(run) / '.write.lock'
    try:
        handle = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as error:
        raise ValueError('Another session write is active; inspect the lock before retrying') from error
    try:
        os.close(handle)
        yield
    finally:
        path.unlink()


def commit(run, state, event):
    state['revision'] += 1
    state['updated_at'] = now()
    state['events'].append({'revision': state['revision'], 'time': now(), **event})
    history = Path(run) / 'history'
    history.mkdir(exist_ok=True)
    target = history / f"{state['revision']:06d}.json"
    if target.exists():
        raise ValueError('History collision; no overwrite allowed')
    payload = json.dumps(state, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
    with tempfile.NamedTemporaryFile('w', dir=history, prefix='.pending-', delete=False, encoding='utf-8') as tmp:
        tmp.write(payload)
        tmp.flush()
        os.fsync(tmp.fileno())
        temporary = Path(tmp.name)
    try:
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            temporary.unlink()
    return state


def init(run, brief, root=ROOT):
    run = local_run(run, root)
    run_id = valid_id(run.name)
    brief_path = Path(brief).resolve()
    brief = read(brief_path)
    for key in ('title', 'scientific_source', 'mechanism'):
        if not isinstance(brief.get(key), str) or not brief[key].strip():
            raise ValueError(f'Missing scientific brief: {key}')
    for key in ('must_show', 'must_not_show'):
        if not isinstance(brief.get(key), list) or any(not isinstance(x, str) for x in brief[key]):
            raise ValueError(f'Expected text list: {key}')
    if not brief['must_show']:
        raise ValueError('must_show cannot be empty')
    run.mkdir(parents=True, exist_ok=False)
    state = {'schema_version': 1, 'run_id': run_id, 'private': True,
             'created_at': now(), 'revision': 0,
             'brief': {'path': str(brief_path), 'sha256': sha(brief_path), 'content': brief},
             'artifacts': {}, 'active': {}, 'checks': [], 'approvals': [], 'events': []}
    with lock(run):
        commit(run, state, {'action': 'init'})
    return status(run)


def active(state, role):
    ident = state['active'].get(role)
    if not ident:
        raise ValueError(f'No current {role} artifact')
    return state['artifacts'][ident]


def current(artifact):
    path = Path(artifact['path'])
    return path.is_file() and sha(path) == artifact['sha256']


def require_current(artifact):
    if not current(artifact):
        raise ValueError(f"Artifact changed or missing: {artifact['path']}; register a new version")


def add(run, ident, role, path, slide=1, root=ROOT, replaces=None):
    run = local_run(run, root)
    valid_id(ident)
    if role not in ROLES or type(slide) is not int or slide < 1:
        raise ValueError('Invalid artifact role or slide number')
    path = Path(path).resolve()
    if not path.is_file():
        raise ValueError('Artifact must be an existing file')
    if role == 'scene':
        validate_scene(read(path))
    if role == 'pptx':
        inspect_pptx(path, slide)
    with lock(run):
        state = load(run)
        if ident in state['artifacts']:
            raise ValueError('Artifact ID exists; use a new version ID')
        if replaces and (replaces not in state['artifacts'] or state['artifacts'][replaces]['role'] != role):
            raise ValueError('Replacement must identify an existing artifact of the same role')
        state['artifacts'][ident] = {'id': ident, 'role': role, 'path': str(path),
            'sha256': sha(path), 'slide': slide, 'registered_revision': state['revision']+1}
        if role in ('source','reference'):
            key = 'sources' if role == 'source' else 'references'
            current_ids = state['active'].setdefault(key, [])
            if replaces:
                if replaces not in current_ids:
                    raise ValueError('Replacement must identify a current input')
                current_ids.remove(replaces)
            current_ids.append(ident)
        else:
            state['active'][role] = ident
        commit(run, state, {'action': 'add', 'artifact': ident, 'role': role})
    return status(run)


def subjects(state, kind):
    roles = {'scientific': ('scene',), 'visual': ('scene', 'pptx', 'preview'),
             'selection': ('scene',), 'native': ('scene', 'pptx')}[kind]
    result = {}
    for role in roles:
        artifact = active(state, role)
        require_current(artifact)
        result[role] = artifact['sha256']
        if role == 'pptx':
            result['pptx_slide'] = artifact['slide']
    if kind == 'native':
        mapping = Path(active(state,'pptx')['path']).with_suffix('.object-map.json')
        if not mapping.is_file():
            raise ValueError('Current native export mapping is missing')
        result['object_map'] = sha(mapping)
    if kind == 'scientific':
        require_current(state['brief'])
        result['brief'] = state['brief']['sha256']
        for ident in state['active'].get('sources',[]):
            record = state['artifacts'][ident]
            require_current(record)
            result['source:'+ident] = record['sha256']
    return result


def check(run, kind, evidence, verdict='pass', root=ROOT):
    run = local_run(run, root)
    if kind not in CHECKS or not isinstance(evidence, str) or not evidence.strip() or verdict not in ('pass', 'fail'):
        raise ValueError('Provide an explicit supported check and evidence of what was actually inspected')
    with lock(run):
        state = load(run)
        state['checks'].append({'kind': kind, 'subjects': subjects(state, kind), 'verdict': verdict,
                                'evidence': evidence, 'method': 'reviewer-attestation', 'time': now()})
        commit(run, state, {'action': 'check', 'kind': kind, 'verdict': verdict})
    return status(run)


def approve(run, ident, evidence, root=ROOT):
    run = local_run(run, root)
    if not isinstance(evidence, str) or not evidence.strip():
        raise ValueError('Quote the actual user approval; approval cannot be inferred')
    with lock(run):
        state = load(run)
        artifact = state['artifacts'].get(ident)
        if not artifact or artifact['role'] not in ('candidate', 'scene'):
            raise ValueError('Approve a registered candidate or scene')
        require_current(artifact)
        state['approvals'].append({'artifact': ident, 'sha256': artifact['sha256'],
                                   'user_evidence': evidence, 'time': now(), 'scope': 'visual-acceptance-not-publication'})
        commit(run, state, {'action': 'user-approval', 'artifact': ident})
    return status(run)


def bound_shapes(state):
    scene_record, pptx = active(state, 'scene'), active(state, 'pptx')
    require_current(scene_record)
    require_current(pptx)
    scene = read(scene_record['path'])
    validate_scene(scene)
    mapping = Path(pptx['path']).with_suffix('.object-map.json')
    if not mapping.is_file():
        raise ValueError('Missing current export mapping; re-export or reconcile the edited PPTX first')
    rows = [x for x in read(mapping) if x.get('slide_number') == pptx['slide']]
    if len(rows) != 1:
        raise ValueError('Ambiguous slide mapping')
    row = rows[0]
    if row.get('scene_sha256') != scene_record['sha256'] or row.get('pptx_sha256') != pptx['sha256'] or row.get('scene_id') != scene['id']:
        raise ValueError('Stale export mapping; do not apply selection IDs to a different version')
    shapes = inspect_pptx(pptx['path'], pptx['slide'])['shapes']
    names = {}
    for shape in shapes:
        if shape['name'] in names:
            raise ValueError('Duplicate PowerPoint object name')
        names[shape['name']] = shape
    mapped = {}
    for obj in row['objects']:
        name = obj['pptx_shape_name']
        if name not in names or str(obj['pptx_shape_id']) != names[name]['pptx_shape_id']:
            raise ValueError('Shape name or native file ID does not match the export map')
        if obj.get('part') != 'arrowhead':
            ident = obj['scene_object_id']
            if ident in mapped:
                raise ValueError('Ambiguous scene object mapping')
            mapped[ident] = names[name]
    for obj in scene['objects']:
        shape = mapped.get(obj['id'])
        expected_type = 'pic' if obj['type'] == 'image' else 'sp'
        if not shape or shape['type'] != expected_type:
            raise ValueError('Required scene object is not a native picture' if expected_type == 'pic'
                             else 'Required scene object is not a native editable shape')
        if obj['type'] == 'text' and shape['text'] != obj['text']:
            raise ValueError('Native text differs from current scene text')
    return scene, mapped


def validate_native(run, root=ROOT):
    run = local_run(run, root)
    with lock(run):
        state = load(run)
        scene, mapped = bound_shapes(state)
        state['checks'].append({'kind': 'native', 'subjects': subjects(state, 'native'),
            'verdict': 'pass', 'method': 'file-shapes-and-hash-bound-map',
            'evidence': {'native_scene_objects': len(scene['objects']), 'matched': len(mapped),
                         'native_pictures': sum(o['type'] == 'image' for o in scene['objects']),
                         'native_shapes': sum(o['type'] != 'image' for o in scene['objects']),
                         'limits': 'Object and text correspondence, not visual rendering or a desktop PowerPoint test'}, 'time': now()})
        commit(run, state, {'action': 'validate-native'})
    return status(run)


def status(run):
    state = load(run)
    current_ids = [x for k, v in state['active'].items() for x in (v if isinstance(v, list) else [v]) if k != 'report']
    stale = [ident for ident in current_ids if not current(state['artifacts'][ident])]
    if not current(state['brief']):
        stale.append('brief')
    passed = {}
    for kind in ('scientific', 'visual', 'selection', 'native'):
        try:
            wanted = subjects(state, kind)
            matches = [x for x in state['checks'] if x['kind'] == kind and x['subjects'] == wanted]
            passed[kind] = bool(matches and matches[-1]['verdict'] == 'pass')
        except ValueError:
            passed[kind] = False
    def accepted(role):
        ident = state['active'].get(role)
        if not ident:
            return False
        return any(x['artifact'] == ident and x['sha256'] == state['artifacts'][ident]['sha256'] for x in state['approvals'])
    if stale:
        stage, action = 'inputs-changed', 'Restore the recorded files or register a new version. Prior checks do not cover changed files.'
    elif not state['active'].get('references'):
        stage, action = 'references', 'Inspect and attach chosen visual references. Use the registry to prepare actual image inputs.'
    elif 'scene' not in state['active']:
        if 'candidate' not in state['active']:
            stage, action = 'design', 'Use the current image skill for visual exploration, or construct a native scene directly when appropriate.'
        elif not accepted('candidate'):
            stage, action = 'design-review', 'Inspect the candidate against the scientific brief and obtain user acceptance before treating it as approved.'
        else:
            stage, action = 'editable', 'Rebuild the accepted design as named editable objects, preserving the scientific brief.'
    elif not all(x in state['active'] for x in ('pptx', 'preview')) or any(active(state,x)['registered_revision'] < active(state,'scene')['registered_revision'] for x in ('pptx','preview')):
        stage, action = 'export', 'Export the current scene to a NEW PPTX, register that file and its rendered preview.'
    elif not all(passed.values()):
        stage, action = 'validation', 'Complete missing checks on the current files: '+', '.join(k for k,v in passed.items() if not v)
    elif not accepted('scene'):
        stage, action = 'user-review', 'Show the checked editable figure. Record only an actual user acceptance, never an assumed one.'
    else:
        stage, action = 'complete', 'The current local figure is accepted and checked. Publication and paper embedding remain separate actions.'
    return {'run_id': state['run_id'], 'revision': state['revision'], 'stage': stage,
            'next_action': action, 'stale': stale, 'checks': passed, 'active': state['active'],
            'private': True, 'note': 'Scientific, visual and selection entries record explicit reviewer evidence; they are not automatic scientific judgments.'}


def selection_request(run, names, shape_ids, operation, output, root=ROOT, allow_semantic_color=False):
    run = local_run(run, root)
    state = load(run)
    scene, mapped = bound_shapes(state)
    if not names and not shape_ids:
        raise ValueError('An exact object name or native file ID is required; screenshot rectangles and app IDs are not file IDs')
    selected = []
    for value, field in [(x,'name') for x in names] + [(str(x),'pptx_shape_id') for x in shape_ids]:
        matches = [ident for ident, shape in mapped.items() if shape[field] == value]
        if len(matches) != 1:
            raise ValueError(f'Ambiguous or unknown selection: {value}')
        if matches[0] not in selected:
            selected.append(matches[0])
    request = {'scene_id': scene['id'], 'selected_ids': selected,
               'expected_sha256': active(state,'scene')['sha256'], 'operations': [operation]}
    if allow_semantic_color:
        request['allow_semantic_color'] = True
    # Validate in memory before creating the request artifact.
    apply_request(scene, request, source_sha256=active(state,'scene')['sha256'])
    output = Path(output).resolve()
    if not output.is_relative_to(run):
        raise ValueError('Selection requests must stay in this private session')
    write_new(output, request)
    return request


def edit(run, request_path, ident, root=ROOT):
    run = local_run(run, root)
    valid_id(ident)
    with lock(run):
        state = load(run)
        source = active(state,'scene')
        require_current(source)
        if ident in state['artifacts']:
            raise ValueError('Artifact ID exists; choose a new version')
        request = read(request_path)
        if request.get('expected_sha256') != source['sha256']:
            raise ValueError('A selection request must match the current scene fingerprint')
        edited, audit = apply_request(read(source['path']), request, source_sha256=source['sha256'])
        output = run / 'edits' / f'{ident}.scene.json'
        audit_path = run / 'edits' / f'{ident}.audit.json'
        if output.exists() or audit_path.exists():
            raise ValueError('Edit outputs already exist')
        write_new(output, edited)
        write_new(audit_path, audit)
        state['artifacts'][ident] = {'id': ident, 'role': 'scene', 'path': str(output),
            'sha256': sha(output), 'slide': source['slide'], 'registered_revision':state['revision']+1}
        state['active']['scene'] = ident
        commit(run, state, {'action':'selected-edit', 'artifact':ident, 'request_sha256':sha(request_path), 'audit':str(audit_path)})
    return status(run)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='command',required=True)
    p=commands.add_parser('init');p.add_argument('--run',type=Path,required=True);p.add_argument('--brief',type=Path,required=True)
    p=commands.add_parser('status');p.add_argument('--run',type=Path,required=True)
    p=commands.add_parser('add');p.add_argument('--run',type=Path,required=True);p.add_argument('--id',required=True);p.add_argument('--role',choices=ROLES,required=True);p.add_argument('--path',type=Path,required=True);p.add_argument('--slide',type=int,default=1);p.add_argument('--replaces')
    p=commands.add_parser('check');p.add_argument('--run',type=Path,required=True);p.add_argument('--kind',choices=CHECKS,required=True);p.add_argument('--evidence',required=True);p.add_argument('--verdict',choices=['pass','fail'],default='pass')
    p=commands.add_parser('approve');p.add_argument('--run',type=Path,required=True);p.add_argument('--id',required=True);p.add_argument('--user-evidence',required=True)
    p=commands.add_parser('validate-native');p.add_argument('--run',type=Path,required=True)
    p=commands.add_parser('selection-request');p.add_argument('--run',type=Path,required=True);p.add_argument('--name',action='append',default=[]);p.add_argument('--shape-id',action='append',default=[]);p.add_argument('--operation',type=json.loads,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--allow-semantic-color',action='store_true')
    p=commands.add_parser('edit');p.add_argument('--run',type=Path,required=True);p.add_argument('--request',type=Path,required=True);p.add_argument('--id',required=True)
    args=parser.parse_args()
    try:
        local_run(args.run)
        if args.command=='init': result=init(args.run,args.brief)
        elif args.command=='status':result=status(args.run)
        elif args.command=='add':result=add(args.run,args.id,args.role,args.path,args.slide,replaces=args.replaces)
        elif args.command=='check':result=check(args.run,args.kind,args.evidence,args.verdict)
        elif args.command=='approve':result=approve(args.run,args.id,args.user_evidence)
        elif args.command=='validate-native':result=validate_native(args.run)
        elif args.command=='selection-request':result=selection_request(args.run,args.name,args.shape_id,args.operation,args.output,allow_semantic_color=args.allow_semantic_color)
        else:result=edit(args.run,args.request,args.id)
        print(json.dumps(result,ensure_ascii=False,indent=2))
    except (ValueError,OSError,KeyError,zipfile.BadZipFile,ET.ParseError) as error:
        parser.exit(2,f'Error: {error}\n')


if __name__=='__main__':
    main()
