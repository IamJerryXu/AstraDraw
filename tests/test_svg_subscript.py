import sys
import unittest
from pathlib import Path
import xml.etree.ElementTree as ET
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from build_components import render_svg

class SvgSubscriptTest(unittest.TestCase):
    def test_missing_font_glyph_is_editable_subscript_and_text_stays_escaped(self):
        scene={'width':200,'height':100,'objects':[{'id':'state','type':'text','role':'label',
               'x':10,'y':10,'width':160,'height':40,'fontSize':30,'fontFamily':'Times New Roman',
               'fill':'black','text':'zₜ < x & y'}]}
        root=ET.fromstring(render_svg(scene))
        ns={'s':'http://www.w3.org/2000/svg'}
        node=root.find('s:text',ns)
        span=node.find('s:tspan',ns)
        self.assertEqual(span.text,'t')
        self.assertEqual(span.get('baseline-shift'),'sub')
        self.assertEqual(''.join(node.itertext()),'zt < x & y')
        self.assertEqual(scene['objects'][0]['text'],'zₜ < x & y')

if __name__=='__main__': unittest.main()
