import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import workflow as wf


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.run=self.root/'.local/runs/example'
        self.brief=self.write('brief.json',{'title':'Example','scientific_source':'Explicit illustrative equation',
            'mechanism':'A deterministic trajectory','must_show':['one source'],'must_not_show':['noise']})
        self.scene={'schema_version':1,'id':'example','width':400,'height':300,'scientific_notes':['Illustration'],
            'objects':[{'id':'label','type':'text','role':'label','x':20,'y':30,'width':100,'height':35,'text':'Source','fontSize':24,'fontFamily':'Times New Roman','fill':'#333333'},
                       {'id':'box','type':'rect','role':'module','x':200,'y':100,'width':50,'height':60,'fill':'#eeeeee','stroke':'none','strokeWidth':0}]}
        self.scene_path=self.write('scene.json',self.scene)
        self.ref=self.root/'ref.png';self.ref.write_bytes(b'private synthetic test fixture')
        self.preview=self.root/'preview.png';self.preview.write_bytes(b'not an actual visual review')

    def write(self,path,value):
        p=self.root/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value));return p

    def init(self):
        return wf.init(self.run,self.brief,root=self.root)

    def add(self,ident,role,path,slide=1):
        return wf.add(self.run,ident,role,path,slide,root=self.root)

    def pptx(self):
        p=self.root/'test.pptx'
        with zipfile.ZipFile(p,'w') as z:
            z.writestr('ppt/slides/slide1.xml','''<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><p:cSld><p:spTree>
            <p:sp><p:nvSpPr><p:cNvPr id="3" name="label"/></p:nvSpPr><p:spPr><a:prstGeom prst="rect"/></p:spPr><p:txBody><a:p><a:r><a:t>Source</a:t></a:r></a:p></p:txBody></p:sp>
            <p:sp><p:nvSpPr><p:cNvPr id="4" name="box"/></p:nvSpPr><p:spPr><a:prstGeom prst="rect"/></p:spPr></p:sp>
            </p:spTree></p:cSld></p:sld>''')
        self.write('test.object-map.json',[{'scene_id':'example','scene_sha256':wf.sha(self.scene_path),'pptx_sha256':wf.sha(p),'slide_number':1,
            'objects':[{'pptx_shape_id':str(i),'pptx_shape_name':name,'scene_object_id':name} for i,name in [(3,'label'),(4,'box')]]}])
        return p

    def ready(self):
        self.init();self.add('ref','reference',self.ref);self.add('scene','scene',self.scene_path)
        self.deck=self.pptx();self.add('deck','pptx',self.deck);self.add('preview','preview',self.preview)

    def attest(self):
        for kind in wf.CHECKS:
            wf.check(self.run,kind,'Synthetic test evidence, not a real visual/scientific judgment',root=self.root)
        wf.validate_native(self.run,root=self.root)

    def test_init_validation_and_private_location(self):
        self.assertEqual(self.init()['stage'],'references')
        with self.assertRaises(FileExistsError):self.init()
        with self.assertRaises(ValueError):wf.init(self.root/'public',self.brief,root=self.root)

    def test_bad_brief_leaves_no_run(self):
        self.write('brief.json',{'title':'Incomplete'})
        with self.assertRaises(ValueError):self.init()
        self.assertFalse(self.run.exists())

    def test_history_versions_survive_resume(self):
        self.init();original=(self.run/'history/000001.json').read_bytes()
        self.add('ref','reference',self.ref)
        self.assertEqual(wf.load(self.run)['revision'],2)
        self.assertEqual((self.run/'history/000001.json').read_bytes(),original)
        self.assertEqual(wf.status(self.run)['stage'],'design')

    def test_duplicate_id_does_not_modify_state(self):
        self.init();self.add('ref','reference',self.ref)
        before=copy.deepcopy(wf.load(self.run))
        with self.assertRaises(ValueError):self.add('ref','reference',self.preview)
        self.assertEqual(wf.load(self.run),before)

    def test_changes_invalidate_status_and_checks(self):
        self.ready();self.attest();wf.approve(self.run,'scene','User explicitly approves example',root=self.root)
        self.assertEqual(wf.status(self.run)['stage'],'complete')
        self.preview.write_bytes(b'changed file')
        self.assertEqual(wf.status(self.run)['stage'],'inputs-changed')
        self.assertFalse(wf.status(self.run)['checks']['visual'])

    def test_approval_alone_never_completes(self):
        self.ready()
        self.assertEqual(wf.approve(self.run,'scene','Confirmed by user',root=self.root)['stage'],'validation')
        with self.assertRaises(ValueError):wf.approve(self.run,'scene','',root=self.root)

    def test_checks_without_user_evidence_require_review(self):
        self.ready();self.attest()
        self.assertEqual(wf.status(self.run)['stage'],'user-review')
        wf.check(self.run,'visual','A visible overlap remains','fail',root=self.root)
        self.assertFalse(wf.status(self.run)['checks']['visual'])

    def test_stale_native_mapping_fails(self):
        self.ready()
        mapping=self.root/'test.object-map.json';data=json.loads(mapping.read_text());data[0]['pptx_sha256']='0'*64;mapping.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError,'Stale'):wf.validate_native(self.run,root=self.root)

    def test_mapping_change_invalidates_previous_native_check(self):
        self.ready();wf.validate_native(self.run,root=self.root)
        self.assertTrue(wf.status(self.run)['checks']['native'])
        p=self.root/'test.object-map.json'
        p.write_text(p.read_text()+'\n')
        self.assertFalse(wf.status(self.run)['checks']['native'])

    def test_selection_name_and_native_id_are_grounded(self):
        self.ready()
        request=wf.selection_request(self.run,['label'],[],{'op':'move','dx':0,'dy':8},self.run/'request.json',root=self.root)
        self.assertEqual(request['selected_ids'],['label'])
        self.assertEqual(request['expected_sha256'],wf.sha(self.scene_path))
        r=wf.selection_request(self.run,[],['4'],{'op':'move','dx':3,'dy':0},self.run/'box-request.json',root=self.root)
        self.assertEqual(r['selected_ids'],['box'])
        with self.assertRaises(ValueError):wf.selection_request(self.run,[],['146'],{'op':'move','dx':0,'dy':8},self.run/'bad.json',root=self.root)
        self.assertFalse((self.run/'bad.json').exists())

    def test_selected_edit_preserves_protected_objects_and_resets_export(self):
        self.ready();self.attest();wf.approve(self.run,'scene','Approved',root=self.root)
        original=self.scene_path.read_bytes()
        req=self.run/'selection.json'
        wf.selection_request(self.run,['label'],[],{'op':'move','dx':0,'dy':8},req,root=self.root)
        result=wf.edit(self.run,req,'scene-v2',root=self.root)
        edited=wf.read(self.run/'edits/scene-v2.scene.json')
        self.assertEqual(edited['objects'][0]['y'],38)
        self.assertEqual(edited['objects'][1],self.scene['objects'][1])
        self.assertEqual(self.scene_path.read_bytes(),original)
        self.assertEqual(result['stage'],'export')
        self.assertFalse(result['checks']['native'])
        with self.assertRaises(ValueError):wf.edit(self.run,req,'scene-v3',root=self.root)

    def test_selection_no_overwrite_and_no_public_path(self):
        self.ready();out=self.run/'selection.json'
        args=(self.run,['label'],[],{'op':'move','dx':0,'dy':8})
        wf.selection_request(*args,out,root=self.root)
        with self.assertRaises(FileExistsError):wf.selection_request(*args,out,root=self.root)
        with self.assertRaises(ValueError):wf.selection_request(*args,self.root/'public.json',root=self.root)

    def test_candidate_path_and_approval_do_not_require_native_first(self):
        self.init();self.add('ref','reference',self.ref);self.add('candidate','candidate',self.preview)
        self.assertEqual(wf.status(self.run)['stage'],'design-review')
        self.assertEqual(wf.approve(self.run,'candidate','User accepts concept',root=self.root)['stage'],'editable')

    def test_replacing_changed_reference_keeps_history_without_permanent_stale_status(self):
        self.init();self.add('old-ref','reference',self.ref)
        old_hash=wf.load(self.run)['artifacts']['old-ref']['sha256']
        self.ref.write_bytes(b'new reference version')
        self.assertEqual(wf.status(self.run)['stage'],'inputs-changed')
        wf.add(self.run,'new-ref','reference',self.ref,root=self.root,replaces='old-ref')
        self.assertEqual(wf.status(self.run)['stage'],'design')
        self.assertEqual(wf.load(self.run)['artifacts']['old-ref']['sha256'],old_hash)

    def test_paper_source_version_is_bound_to_scientific_review(self):
        self.ready();self.add('paper','source',self.brief)
        wf.check(self.run,'scientific','Read stated source',root=self.root)
        self.assertTrue(wf.status(self.run)['checks']['scientific'])
        source2=self.write('source-v2.json',{'updated':'scientific content'})
        wf.add(self.run,'paper-v2','source',source2,root=self.root,replaces='paper')
        self.assertFalse(wf.status(self.run)['checks']['scientific'])

    def test_semantic_color_change_requires_explicit_selection_permission(self):
        self.scene['objects'][1]['semantic_color']=True
        self.write('scene.json',self.scene)
        self.ready()
        args=(self.run,['box'],[],{'op':'set','properties':{'fill':'#990000'}},self.run/'color.json')
        with self.assertRaises(ValueError):wf.selection_request(*args,root=self.root)
        r=wf.selection_request(*args,root=self.root,allow_semantic_color=True)
        self.assertTrue(r['allow_semantic_color'])


if __name__=='__main__':unittest.main()
