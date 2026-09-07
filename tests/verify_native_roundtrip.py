"""Read-only native PPTX fidelity check; an optional new report stays private."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile
import xml.etree.ElementTree as ET

NS={'p':'http://schemas.openxmlformats.org/presentationml/2006/main','a':'http://schemas.openxmlformats.org/drawingml/2006/main'}


def verify(deck, reference_previews=None):
    mapping=json.loads(deck.with_suffix('.object-map.json').read_text())
    digest=hashlib.sha256(deck.read_bytes()).hexdigest()
    checks=[]
    with zipfile.ZipFile(deck) as package:
        assert not [n for n in package.namelist() if n.startswith('ppt/media/')], 'Unexpected raster media'
        slide_paths=[n for n in package.namelist() if re.fullmatch(r'ppt/slides/slide\d+\.xml',n)]
        assert len(slide_paths)==len(mapping), 'Slide count mismatch'
        for page in mapping:
            source=Path(page['source_scene_path']);data=source.read_bytes();scene=json.loads(data)
            assert hashlib.sha256(data).hexdigest()==page['scene_sha256'], 'Stale scene mapping'
            assert digest==page['pptx_sha256'], 'Stale PPTX mapping'
            assert scene['id']==page['scene_id']
            root=ET.fromstring(package.read(f'ppt/slides/slide{page["slide_number"]}.xml'))
            shapes=root.findall('.//p:sp',NS)
            by_name={s.find('p:nvSpPr/p:cNvPr',NS).get('name'):s for s in shapes}
            assert len(by_name)==len(shapes)==len(page['objects']), 'Duplicate or missing native objects'
            assert not root.findall('.//p:pic',NS), 'Raster image found'
            for record in page['objects']:
                s=by_name[record['pptx_shape_name']]
                assert s.find('p:nvSpPr/p:cNvPr',NS).get('id')==record['pptx_shape_id']
            for obj in scene['objects']:
                shape=by_name[obj['id']]
                if obj['type']=='text':
                    assert ''.join(e.text or '' for e in shape.findall('.//a:t',NS))==obj['text']
                    if obj.get('italic'):assert shape.findall('.//a:rPr[@i="1"]',NS), 'Italic style lost'
                else:
                    if obj.get('dotted'):assert shape.findall('p:spPr/a:ln/a:prstDash[@val="dot"]',NS), 'Dotted style lost'
                    if obj['type']=='polyline':
                        geom=shape.find('p:spPr/a:custGeom',NS);assert geom is not None
                        assert len(geom.findall('.//a:moveTo',NS))+len(geom.findall('.//a:lnTo',NS))==len(obj['points']), 'Polyline vertices changed'
                    for key,location in [('fill','p:spPr/a:solidFill/a:srgbClr'),('stroke','p:spPr/a:ln/a:solidFill/a:srgbClr')]:
                        rgba=re.fullmatch(r'rgba\((\d+),(\d+),(\d+),([\d.]+)\)',obj.get(key,''))
                        if rgba:
                            color=shape.find(location,NS);assert color is not None
                            assert color.get('val').upper()==''.join(f'{int(v):02X}' for v in rgba.groups()[:3]), 'RGB color changed'
                            assert abs(int(color.find('a:alpha',NS).get('val'))-float(rgba.group(4))*100000)<=1,'Transparency changed'
            pixel_equal=None
            if reference_previews:
                from PIL import Image,ImageChops
                actual=Image.open(deck.with_name(deck.stem+'-previews')/(scene['id']+'.png')).convert('RGB')
                reference=Image.open(reference_previews/(scene['id']+'-v3.png')).convert('RGB')
                assert actual.size==reference.size
                pixel_equal=ImageChops.difference(actual,reference).getbbox() is None
                assert pixel_equal,'Rendered slide differs from approved reference'
            checks.append(dict(scene_id=scene['id'],slide=page['slide_number'],native_objects=len(shapes),pixel_equal=pixel_equal))
    return dict(status='pass',pptx_sha256=digest,slides=checks)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('deck',type=Path);parser.add_argument('--reference-previews',type=Path);parser.add_argument('--report',type=Path);args=parser.parse_args()
    result=verify(args.deck,args.reference_previews)
    if args.report:
        with args.report.open('x') as f: json.dump(result,f,indent=2)
    print(json.dumps(result,indent=2))
