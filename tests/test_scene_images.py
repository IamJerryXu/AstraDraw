"""Image source, immutable edits and real native picture export regression checks."""
import base64
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from build_components import render_svg
from selection_edit import apply_request, validate_scene
import workflow as wf

PNG = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII='
JPEG = '/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAABAAEDASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwD5/ooooA//2Q=='
NODE = str(Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node')


def scene():
    return {'schema_version':1,'id':'image-fixture','width':300,'height':200,'objects':[
        {'id':'photo','type':'image','role':'source-photo','x':20,'y':20,'width':100,'height':50,
         'src':'data:image/png;base64,'+PNG,'src_sha256':hashlib.sha256(base64.b64decode(PNG)).hexdigest(),
         'alt':'One pixel fixture','provenance':{'kind':'literal-test-fixture'}},
        {'id':'label','type':'text','role':'label','x':160,'y':20,'width':120,'height':30,
         'text':'Independent label','fontFamily':'Arial','fontSize':14,'fill':'#111111'}]}


class ImageTests(unittest.TestCase):
    def test_svg_embeds_original_and_preserves_aspect_and_metadata(self):
        value=scene();root=ET.fromstring(render_svg(value))
        pic=root.find('{http://www.w3.org/2000/svg}image')
        self.assertEqual(pic.get('href'),value['objects'][0]['src'])
        self.assertEqual(pic.get('preserveAspectRatio'),'xMidYMid meet')
        self.assertIn('literal-test-fixture',ET.tostring(pic).decode())

    def test_move_preserves_image_bytes_metadata_and_unselected_objects(self):
        value=scene();before=copy.deepcopy(value)
        changed,audit=apply_request(value,{'scene_id':value['id'],'selected_ids':['photo'],
                                        'operations':[{'op':'move','dx':5,'dy':8}]})
        self.assertEqual(value,before)
        expected=copy.deepcopy(before['objects'][0]);expected.update(x=25,y=28)
        self.assertEqual(changed['objects'][0],expected)
        self.assertEqual(changed['objects'][1],before['objects'][1])
        self.assertTrue(audit['no_unselected_drift'])
        self.assertEqual(audit['changed_ids'],['photo'])

    def test_unsafe_sources_hash_mismatch_and_cropping_rejected(self):
        for update in ({'src':'https://example.com/photo.png'}, {'src':'../photo.png'},
                       {'src_sha256':'0'*64}, {'fit':'cover'},
                       {'src':'data:image/png;base64,YmFk'}):
            with self.subTest(update=update):
                value=scene();value['objects'][0].update(update)
                with self.assertRaises(ValueError):validate_scene(value)
                with self.assertRaises(ValueError):render_svg(value)

    def test_native_preflight_accepts_png_and_rejects_network(self):
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)/'scene.json';output=Path(directory)/'out.pptx'
            code='import {preflight} from '+json.dumps((ROOT/'scripts/export_components.mjs').as_uri())+'; await preflight({scenes:['+json.dumps(str(source))+'],output:'+json.dumps(str(output))+'});'
            value=scene();source.write_text(json.dumps(value))
            result=subprocess.run([NODE,'--input-type=module','-e',code],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            value['objects'][0]['src']='https://example.com/photo.png';source.write_text(json.dumps(value))
            self.assertNotEqual(subprocess.run([NODE,'--input-type=module','-e',code],capture_output=True).returncode,0)

    @unittest.skipUnless(os.environ.get('AFW_TEST_IMAGE_EXPORT')=='1','Explicit authoring marker required for real PPTX test')
    def test_real_native_picture_export_mapping_and_workflow_count(self):
        # Private evidence remains available for visual inspection after the test.
        directory=Path(tempfile.mkdtemp(prefix='image-regression-',dir=ROOT/'.local'))
        value=scene()
        second=copy.deepcopy(value['objects'][0]);second.update(id='jpeg-photo',y=110,src='data:image/jpeg;base64,'+JPEG,src_sha256=hashlib.sha256(base64.b64decode(JPEG)).hexdigest())
        value['objects'].append(second)
        source=directory/'scene.json';source.write_text(json.dumps(value))
        output=directory/'output/figure.pptx'
        result=subprocess.run([NODE,str(ROOT/'scripts/export_components.mjs'),'--scene',str(source),
                               '--output',str(output),'--build-dir',str(directory/'build')],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        mapping=json.loads(output.with_suffix('.object-map.json').read_text())[0]
        record=next(o for o in mapping['objects'] if o['scene_object_id']=='photo')
        ns={'p':'http://schemas.openxmlformats.org/presentationml/2006/main'}
        with zipfile.ZipFile(output) as deck:
            root=ET.fromstring(deck.read('ppt/slides/slide1.xml'))
            pic=root.find('.//p:pic/p:nvPicPr/p:cNvPr',ns)
            self.assertEqual(pic.get('name'),'photo')
            self.assertEqual(pic.get('id'),record['pptx_shape_id'])
            self.assertEqual(len(root.findall('.//p:sp',ns)),1)
            self.assertEqual(len(root.findall('.//p:pic',ns)),2)
            self.assertIn(base64.b64decode(PNG),[deck.read(n) for n in deck.namelist() if n.startswith('ppt/media/')])
            self.assertIn(base64.b64decode(JPEG),[deck.read(n) for n in deck.namelist() if n.startswith('ppt/media/')])
        brief=directory/'brief.json';brief.write_text(json.dumps({'title':'Image test','scientific_source':'Test fixture','mechanism':'No scientific claim','must_show':['photo','label'],'must_not_show':['flattened diagram']}))
        run=directory/'run';wf.init(run,brief)
        wf.add(run,'scene','scene',source)
        wf.add(run,'deck','pptx',output)
        wf.validate_native(run)
        evidence=wf.load(run)['checks'][-1]['evidence']
        self.assertEqual(evidence['native_pictures'],2)
        self.assertEqual(evidence['native_shapes'],1)
        request=wf.selection_request(run,[],[record['pptx_shape_id']],{'op':'move','dx':5,'dy':8},run/'request.json')
        self.assertEqual(request['selected_ids'],['photo'])
        moved,audit=apply_request(value,request,wf.sha(source))
        self.assertEqual(moved['objects'][1:],value['objects'][1:])
        moved_source=directory/'moved.json';moved_source.write_text(json.dumps(moved))
        moved_output=directory/'output/moved.pptx'
        result=subprocess.run([NODE,str(ROOT/'scripts/export_components.mjs'),'--scene',str(moved_source),
                               '--output',str(moved_output),'--build-dir',str(directory/'build')],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        def frames(deck_path):
            with zipfile.ZipFile(deck_path) as deck:
                xml=ET.fromstring(deck.read('ppt/slides/slide1.xml'))
            namespaces={**ns,'a':'http://schemas.openxmlformats.org/drawingml/2006/main'}
            return {pic.find('p:nvPicPr/p:cNvPr',namespaces).get('name'):
                    dict(pic.find('p:spPr/a:xfrm/a:off',namespaces).attrib)
                    for pic in xml.findall('.//p:pic',namespaces)}
        before,after=frames(output),frames(moved_output)
        self.assertEqual(after['jpeg-photo'],before['jpeg-photo'])
        self.assertEqual(int(after['photo']['x'])-int(before['photo']['x']),5*9525)
        self.assertEqual(int(after['photo']['y'])-int(before['photo']['y']),8*9525)
        print('Native image evidence:',directory)


if __name__=='__main__':unittest.main()
