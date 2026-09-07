"""Bind picture names after checking source order, original bytes and contain frames."""
import hashlib
import json
import posixpath
import sys
import zipfile
from xml.dom import minidom

P = 'http://schemas.openxmlformats.org/presentationml/2006/main'
A = 'http://schemas.openxmlformats.org/drawingml/2006/main'
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'


def bind(source, output, slides):
    with zipfile.ZipFile(source) as src, zipfile.ZipFile(output, 'x') as dest:
        for info in src.infolist():
            data = src.read(info.filename)
            if info.filename.startswith('ppt/slides/slide') and info.filename.endswith('.xml'):
                index = int(info.filename.rsplit('slide', 1)[1].split('.')[0]) - 1
                expected = slides[index]
                doc = minidom.parseString(data)
                pictures = doc.getElementsByTagNameNS(P, 'pic')
                if len(pictures) != len(expected):
                    raise ValueError('Native picture count differs from the scene')
                relpath = 'ppt/slides/_rels/slide'+str(index+1)+'.xml.rels'
                rels = minidom.parseString(src.read(relpath)) if expected else None
                targets = {r.getAttribute('Id'):r.getAttribute('Target') for r in rels.getElementsByTagName('Relationship')} if rels else {}
                for pic, obj in zip(pictures, expected):
                    props = pic.getElementsByTagNameNS(P, 'cNvPr')
                    if len(props) != 1:
                        raise ValueError('Ambiguous picture identity')
                    prop = props[0]
                    blip = pic.getElementsByTagNameNS(A, 'blip')[0]
                    target = targets.get(blip.getAttributeNS(R, 'embed'), '')
                    media = posixpath.normpath(posixpath.join('ppt/slides', target)) if not target.startswith('/') else target.lstrip('/')
                    if not target or hashlib.sha256(src.read(media)).hexdigest() != obj['sha256']:
                        raise ValueError('Native picture source bytes differ from the scene')
                    xfrm = pic.getElementsByTagNameNS(A, 'xfrm')[0]
                    off = xfrm.getElementsByTagNameNS(A, 'off')[0]
                    ext = xfrm.getElementsByTagNameNS(A, 'ext')[0]
                    x,y,w,h = [float(n.getAttribute(k))/9525 for n,k in ((off,'x'),(off,'y'),(ext,'cx'),(ext,'cy'))]
                    if (abs(x+w/2-obj['x']-obj['width']/2)>.02 or abs(y+h/2-obj['y']-obj['height']/2)>.02
                            or w>obj['width']+.02 or h>obj['height']+.02
                            or min(abs(w-obj['width']),abs(h-obj['height']))>.02):
                        raise ValueError('Native picture position differs from the scene contain frame')
                    prop.setAttribute('name', obj['id'])
                    prop.setAttribute('descr', obj['alt'])
                if expected:
                    data = doc.toxml(encoding='UTF-8')
            dest.writestr(info, data)


if __name__ == '__main__':
    bind(sys.argv[1], sys.argv[2], json.loads(sys.argv[3]))
