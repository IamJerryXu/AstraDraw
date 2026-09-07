"""Forward export contracts, including immutable outputs and SVG style fidelity."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('build_components', ROOT/'scripts/build_components.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)
NODE = os.environ.get('RUNTIME_NODE', str(Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node'))


def scene():
    return dict(id='fixture',width=300,height=200,objects=[
        dict(id='label',type='text',role='label',x=10,y=10,width=100,height=30,text='p₀',fontFamily='Times New Roman',fontSize=24,fill='rgba(10,20,30,0.5)',italic=True),
        dict(id='path',type='polyline',role='trajectory',points=[[10,70],[200,70]],fill='none',stroke='rgba(100,150,200,0.25)',strokeWidth=2,dotted=True,endArrow=True),
        dict(id='path--arrow',type='polyline',role='arrowhead',points=[[200,70],[190,65],[190,75]],fill='rgba(100,150,200,0.25)',stroke='none',strokeWidth=0,closed=True),
    ])


class SvgExportTests(unittest.TestCase):
    def test_styles_and_explicit_arrow_are_preserved(self):
        root=ET.fromstring(builder.render_svg(scene()))
        by_id={e.get('id'):e for e in root if e.get('id')}
        self.assertEqual(len([e for e in root if e.get('id')=='path--arrow']),1)
        self.assertEqual(by_id['label'].get('font-style'),'italic')
        self.assertEqual(by_id['label'].get('fill'),'#0A141E')
        self.assertEqual(by_id['label'].get('fill-opacity'),'0.5')
        self.assertEqual(by_id['path'].get('stroke-dasharray'),'1 6')
        self.assertEqual(by_id['path'].get('stroke-opacity'),'0.25')

    def test_cli_refuses_existing_svg(self):
        with tempfile.TemporaryDirectory() as d:
            source=Path(d)/'source.json';source.write_text(json.dumps(scene()))
            dest=Path(d)/'keep.svg';dest.write_text('original')
            result=subprocess.run(['python3',str(ROOT/'scripts/build_components.py'),'--scene',str(source),'--output',str(dest)],capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            self.assertEqual(dest.read_text(),'original')

    def test_cli_requires_explicit_catalog_creation(self):
        result=subprocess.run(['python3',str(ROOT/'scripts/build_components.py')],capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('--rebuild-catalog',result.stderr)


@unittest.skipUnless(Path(NODE).exists(),'Bundled Node unavailable')
class NativePreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.directory=Path(self.temp.name)
        self.source=self.directory/'a.json';self.source.write_text(json.dumps(scene()))
        self.output=self.directory/'new.pptx'

    def run_js(self,body):
        code='import {parseArguments,preflight,lineStyle,needsArrow} from '+json.dumps((ROOT/'scripts/export_components.mjs').as_uri())+';\n'+body
        return subprocess.run([NODE,'--input-type=module','-e',code],capture_output=True,text=True)

    def preflight(self,extra=None):
        args=['--scene',str(self.source),*(extra or []),'--output',str(self.output)]
        return self.run_js('console.log(JSON.stringify(await preflight(parseArguments('+json.dumps(args)+'))));')

    def test_single_scene_compatible_and_hash_bound(self):
        import hashlib
        result=self.preflight();self.assertEqual(result.returncode,0,result.stderr)
        data=json.loads(result.stdout)
        self.assertEqual(data['sourceHashes'],[hashlib.sha256(self.source.read_bytes()).hexdigest()])
        self.assertEqual(data['previewDir'],str(self.directory/'new-previews'))
        self.assertFalse(self.output.exists())

    def test_default_catalog_excludes_retired_font_demos(self):
        args=['--output',str(self.output)]
        result=self.run_js('console.log(JSON.stringify(await preflight(parseArguments('+json.dumps(args)+'))));')
        self.assertEqual(result.returncode,0,result.stderr)
        ids={s['id'] for s in json.loads(result.stdout)['scenes']}
        self.assertFalse(ids & {'ode-comic','ode-roman','ode-modern'})
        self.assertIn('sde-comic',ids)
        self.assertIn('flow-matching-modern',ids)
        self.assertFalse(self.output.exists())

    def test_explicit_historical_scene_remains_available(self):
        args=['--scene',str(ROOT/'components/ode/ode-comic.json'),'--output',str(self.output)]
        result=self.run_js('console.log(JSON.stringify(await preflight(parseArguments('+json.dumps(args)+'))));')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual([s['id'] for s in json.loads(result.stdout)['scenes']],['ode-comic'])
        self.assertFalse(self.output.exists())

    def test_repeat_scene_preserves_page_order(self):
        other=scene();other['id']='second';p=self.directory/'b.json';p.write_text(json.dumps(other))
        result=self.preflight(['--scene',str(p)]);self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual([s['id'] for s in json.loads(result.stdout)['scenes']],['fixture','second'])

    def test_mixed_canvas_rejected_without_output(self):
        other=scene();other.update(id='second',height=201);p=self.directory/'b.json';p.write_text(json.dumps(other))
        result=self.preflight(['--scene',str(p)])
        self.assertNotEqual(result.returncode,0);self.assertIn('Mixed canvas',result.stderr)
        self.assertFalse(self.output.exists())

    def test_all_output_sidecars_and_dangling_symlinks_protected(self):
        for target in [self.output,self.directory/'new.object-map.json',self.directory/'new.validation.json',self.directory/'new-previews']:
            with self.subTest(target=target.name):
                target.write_text('keep')
                result=self.preflight();self.assertNotEqual(result.returncode,0)
                self.assertIn('Refusing to overwrite',result.stderr);self.assertEqual(target.read_text(),'keep')
                target.unlink()
        self.output.symlink_to(self.directory/'missing.pptx')
        self.assertNotEqual(self.preflight().returncode,0)
        self.assertTrue(self.output.is_symlink())

    def test_duplicate_scene_ids_and_unsafe_ids_rejected(self):
        self.assertNotEqual(self.preflight(['--scene',str(self.source)]).returncode,0)
        bad=scene();bad['id']='../escape';self.source.write_text(json.dumps(bad))
        self.assertNotEqual(self.preflight().returncode,0)

    def test_native_dotted_and_explicit_arrows(self):
        result=self.run_js('console.log(JSON.stringify([lineStyle({dotted:true,dashed:true}),needsArrow({id:"path",endArrow:true},new Set(["path--arrow"])),needsArrow({id:"path",endArrow:true},new Set())]));')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout),['dotted',False,True])


if __name__=='__main__':unittest.main()
