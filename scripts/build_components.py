#!/usr/bin/env python3
"""Original illustrative, native-editable mechanism components (no simulation claims)."""
import argparse
import base64
import hashlib
import html
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
THEMES = {
    'comic': dict(font='Comic Sans MS', ink='#263747', blue='#427CA3', coral='#C56856', teal='#428778', pale='#EDF4F7', line=3.4, radius=18),
    'roman': dict(font='Times New Roman', ink='#253445', blue='#3C608C', coral='#AF6545', teal='#577D68', pale='#F1F3F6', line=2.3, radius=2),
    'modern': dict(font='Arial', ink='#172C40', blue='#236B9C', coral='#C15D42', teal='#197D7E', pale='#EEF4F8', line=2.8, radius=8),
}

def validate_image_source(obj):
    """Accept only self-contained PNG/JPEG bytes; never resolve paths or URLs."""
    match = re.fullmatch(r'data:(image/(?:png|jpeg));base64,([A-Za-z0-9+/]+={0,2})', obj.get('src', ''))
    if not match:
        raise ValueError('Image src must be an embedded PNG/JPEG data URI')
    try:
        data = base64.b64decode(match[2], validate=True)
    except ValueError as exc:
        raise ValueError('Invalid image base64') from exc
    if base64.b64encode(data).decode() != match[2] or not (
        data.startswith(b'\x89PNG\r\n\x1a\n') if match[1] == 'image/png'
        else data.startswith(b'\xff\xd8') and data.endswith(b'\xff\xd9')):
        raise ValueError('Invalid image bytes')
    if 'src_sha256' in obj and obj['src_sha256'] != hashlib.sha256(data).hexdigest():
        raise ValueError('Image source hash mismatch')
    if obj.get('fit', 'contain') != 'contain':
        raise ValueError('Image fit must preserve the complete source')
    return data

def render_svg(scene):
    """Render one schema-v1 scene. Returned SVG preserves IDs and editable text."""
    esc = lambda x: html.escape(str(x), quote=True)
    def color_attrs(name, value):
        # Separate alpha for SVG 1.1 readers that cannot parse CSS rgba().
        match = re.fullmatch(r'rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d*\.?\d+)\s*\)', str(value), re.I)
        if match:
            r, g, b = map(int, match.groups()[:3]); alpha = float(match.group(4))
            if max(r, g, b) > 255 or not 0 <= alpha <= 1:
                raise ValueError(f'Invalid RGBA color: {value}')
            return f'{name}="#{r:02X}{g:02X}{b:02X}" {name}-opacity="{alpha:g}"'
        return f'{name}="{esc(value)}"'
    object_ids = {o['id'] for o in scene['objects']}
    lines = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{scene["width"]}" height="{scene["height"]}" viewBox="0 0 {scene["width"]} {scene["height"]}">', '<rect width="100%" height="100%" fill="white"/>']
    for o in scene['objects']:
        attrs = f'id="{esc(o["id"])}" data-role="{esc(o["role"])}"'
        t = o['type']
        if t == 'image':
            validate_image_source(o)
            metadata = esc(json.dumps({k:o[k] for k in ('src_sha256','provenance') if k in o},ensure_ascii=False))
            lines.append(f'<image {attrs} x="{o["x"]}" y="{o["y"]}" width="{o["width"]}" height="{o["height"]}" href="{esc(o["src"])}" preserveAspectRatio="xMidYMid meet"><title>{esc(o.get("alt",o["id"]))}</title><metadata>{metadata}</metadata></image>')
        elif t == 'text':
            baseline = o['y'] + o['height']/2
            # Some SVG readers lack U+209C fallback in Comic/Times. Preserve
            # editable mathematical text with an explicit subscript span.
            text_markup = esc(o['text']).replace('ₜ', '<tspan font-size="70%" baseline-shift="sub">t</tspan>')
            lines.append(f'<text {attrs} x="{o["x"]}" y="{baseline}" dominant-baseline="central" font-family="{esc(o["fontFamily"])}" font-size="{o["fontSize"]}" font-weight="{700 if o.get("bold") else 400}" font-style="{"italic" if o.get("italic") else "normal"}" {color_attrs("fill",o["fill"])}>{text_markup}</text>')
        elif t in ('rect', 'ellipse'):
            geo = (f'x="{o["x"]}" y="{o["y"]}" width="{o["width"]}" height="{o["height"]}" rx="{o.get("radius",0)}"' if t == 'rect' else f'cx="{o["x"]+o["width"]/2}" cy="{o["y"]+o["height"]/2}" rx="{o["width"]/2}" ry="{o["height"]/2}"')
            dash = ' stroke-dasharray="1 6" stroke-linecap="round"' if o.get('dotted') else (' stroke-dasharray="8 7"' if o.get('dashed') else '')
            lines.append(f'<{t} {attrs} {geo} {color_attrs("fill",o["fill"])} {color_attrs("stroke",o["stroke"])} stroke-width="{o["strokeWidth"]}"{dash}/>')
        elif t == 'polyline':
            points = o['points']
            tag = 'polygon' if o.get('closed') else 'polyline'
            dash = ' stroke-dasharray="1 6"' if o.get('dotted') else (' stroke-dasharray="8 7"' if o.get('dashed') else '')
            lines.append(f'<{tag} {attrs} points="'+ ' '.join(f'{x:.3f},{y:.3f}' for x,y in points)+f'" {color_attrs("fill",o.get("fill","none"))} {color_attrs("stroke",o["stroke"])} stroke-width="{o["strokeWidth"]}" stroke-linecap="round" stroke-linejoin="round"{dash}/>')
            if o.get('endArrow') and o['id']+'--arrow' not in object_ids:
                a,b=points[-2:]; angle=math.atan2(b[1]-a[1],b[0]-a[0]); length=10+o['strokeWidth']; wing=length*.43
                q=[b,[b[0]-length*math.cos(angle)+wing*math.sin(angle),b[1]-length*math.sin(angle)-wing*math.cos(angle)],[b[0]-length*math.cos(angle)-wing*math.sin(angle),b[1]-length*math.sin(angle)+wing*math.cos(angle)]]
                lines.append(f'<polygon id="{esc(o["id"])}--arrow" points="'+ ' '.join(f'{x:.3f},{y:.3f}' for x,y in q)+f'" {color_attrs("fill",o["stroke"])}/>')
    return '\n'.join(lines+['</svg>'])

class Builder:
    def __init__(self, component, style):
        self.t=THEMES[style]
        self.scene=dict(schema_version=1,id=f'{component}-{style}',component=component,style=style,width=1200,height=680,scientific_notes=[],objects=[])
    def add(self, ident, typ, role, **kw):
        self.scene['objects'].append(dict(id=ident,type=typ,role=role,**kw))
    def text(self, ident,x,y,w,txt,size=25,color=None,bold=False,group=None):
        self.add(ident,'text','label',x=x,y=y,width=w,height=size*1.5,text=txt,fontFamily=self.t['font'],fontSize=size,fill=color or self.t['ink'],bold=bold,group=group)
    def line(self,ident,pts,color=None,width=None,arrow=False,dashed=False,group=None):
        self.add(ident,'polyline','trajectory' if 'path' in ident else 'connector',points=pts,fill='none',stroke=color or self.t['ink'],strokeWidth=width or self.t['line'],endArrow=arrow,dashed=dashed,group=group)
    def dot(self,ident,x,y,r,color,group=None):
        self.add(ident,'ellipse','state',x=x-r,y=y-r,width=2*r,height=2*r,fill=color,stroke='white',strokeWidth=1.5,group=group,semantic_color=True)
    def box(self,ident,x,y,w,h,fill=None):
        self.add(ident,'rect','mechanism',x=x,y=y,width=w,height=h,fill=fill or self.t['pale'],stroke='none',strokeWidth=0,radius=self.t['radius'])
    def title(self,txt,eq):
        self.text('title',60,32,1060,txt,35,bold=True)
        self.text('equation',60,87,1040,eq,25)
        self.line('heading-rule',[[60,142],[1140,142]],'#CDD5DD',1)
    def axis(self,y=535):
        self.line('time-axis',[[165,y],[1040,y]],'#758595',1.6,True)
        self.text('time-start',148,y+8,110,'t = 0',22)
        self.text('time-end',1006,y+8,100,'t = 1',22)
        self.text('time-label',559,y+8,100,'time',22)
    def footer(self,text): self.text('illustration-note',60,626,1090,text,19,color='#687887')

def ode(style):
    b=Builder('ode',style); t=b.t
    b.title('ODE · deterministic evolution','dx / dt = v(x, t)')
    b.text('initial-label',83,175,200,'Initial states',25)
    b.text('terminal-label',943,175,200,'Final states',25)
    for i,(start,end,clr) in enumerate([(265,245,t['blue']),(350,335,t['teal']),(435,420,t['coral'])]):
        pts=[]
        for k in range(101):
            u=k/100; pts.append([175+850*u,start+(end-start)*u+32*math.sin(math.pi*u)])
        b.line(f'path-{i+1}',pts,clr,arrow=True,group=f'trajectory-{i+1}')
        b.dot(f'initial-{i+1}',175,start,8,clr); b.dot(f'final-{i+1}',1025,end,8,clr)
        # Local velocity shares the direction of the corresponding trajectory.
        j=49; p=pts[j]; q=pts[j+8]
        b.line(f'velocity-{i+1}',[[p[0],p[1]-24],[q[0],q[1]-24]],clr,2.1,True)
    b.text('velocity-label',535,207,240,'Local velocity',22)
    b.axis(); b.footer('Illustration: each initial state follows one trajectory under a well-posed velocity field.')
    b.scene['scientific_notes']=['Original geometric illustration, not numerical integration or empirical data.','Uniqueness requires appropriate regularity of the velocity field. The displayed trajectories do not branch or intersect at equal time.','The horizontal coordinate represents time. Vertical position is an illustrative one-dimensional state coordinate.']
    return b.scene

def sde(style):
    b=Builder('sde',style); t=b.t
    b.title('SDE · drift and stochastic variation','dX = b(X, t) dt + σ(X, t) dW')
    b.text('shared-label',65,237,200,'Shared state',24)
    b.text('realizations-label',828,173,310,'Possible realizations',24)
    for i,(offset,clr) in enumerate([(-95,t['blue']),(10,t['teal']),(95,t['coral'])]):
        pts=[]
        for k in range(121):
            u=k/120
            noise=(math.sin(k*1.8+i*.8)*8+math.sin(k*.55+i)*12)*math.sqrt(u)
            pts.append([175+850*u,335-22*math.sin(math.pi*u)+offset*u+noise])
        b.line(f'path-{i+1}',pts,clr,t['line']*.9,True,group=f'realization-{i+1}')
        b.dot(f'final-{i+1}',*pts[-1],7,clr)
    b.dot('shared-state',175,335,10,t['ink'])
    b.line('drift-key',[[235,458],[310,458]],t['ink'],2.6,True)
    b.text('drift-label',326,441,170,'Drift',23)
    b.line('noise-key',[[525,458],[538,448],[550,467],[563,450],[575,458],[590,444],[605,458]],t['coral'],2.6)
    b.text('noise-label',626,441,320,'Stochastic variation',23)
    b.axis(); b.footer('Illustration: different noise realizations can produce different paths from the same state.')
    b.scene['scientific_notes']=['Original hand-designed noisy paths. They are illustrative and are not simulated Brownian or SDE sample paths.','A common initial state is shown under different noise realizations. Smooth baseline intuition is not a claim about the expected solution.','State-dependent drift and diffusion may produce behavior different from this example.']
    return b.scene

def fm(style):
    b=Builder('flow-matching',style); t=b.t
    b.title('Flow Matching · training and sampling','Example: straight conditional interpolation')
    b.text('training-label',60,173,250,'Training',27,bold=True)
    b.text('interpolation-equation',300,173,790,'xₜ = (1 − t)x₀ + tx₁      target velocity: x₁ − x₀',24)
    for i,(y0,y1) in enumerate([(278,247),(352,325)]):
        clr=[t['blue'],t['coral']][i]; x0=180; x1=1030
        b.line(f'conditional-path-{i+1}',[[x0,y0],[x1,y1]],clr,t['line']*.85,True,group='training')
        b.dot(f'paired-source-{i+1}',x0,y0,8,clr); b.dot(f'paired-target-{i+1}',x1,y1,8,clr)
        xm=590; ym=y0+(y1-y0)*(xm-x0)/(x1-x0)
        b.dot(f'training-sample-{i+1}',xm,ym,7,clr)
        b.line(f'target-velocity-{i+1}',[[xm,ym-22],[xm+82,ym-22+(y1-y0)*82/850]],clr,2.8,True)
    b.text('source-label',135,370,190,'Source samples',21)
    b.text('target-label',944,370,210,'Paired targets',21)
    b.line('stage-rule',[[60,418],[1140,418]],'#CDD5DD',1)
    b.text('sampling-label',60,439,230,'Sampling',27,bold=True)
    b.text('sampling-equation',300,439,810,'dx / dt = vθ(x, t)',24)
    pts=[]
    for k in range(101):
        u=k/100; pts.append([180+850*u,548-35*math.sin(math.pi*u)+8*math.sin(2*math.pi*u)])
    b.line('learned-ode-path',pts,t['teal'],t['line']*1.1,True,group='sampling')
    b.dot('sampling-source',180,548,8,t['teal']); b.dot('generated-state',1030,548,8,t['teal'])
    b.text('prior-label',141,568,210,'Prior sample',21)
    b.text('generated-label',958,568,190,'Generated',21)
    b.footer('Illustration: training pairs define supervision. Sampling integrates the learned velocity field.')
    b.scene['scientific_notes']=['Original geometric illustration, not a trained model or numerical simulation.','The training example uses straight conditional interpolation between a source-target pair. This is one choice, not a universal Flow Matching path.','Target velocity x1-x0 belongs to this conditional path. The learned marginal velocity field can yield curved sampling trajectories.','The two training pairs do not assert a specific coupling algorithm. Sampling starts from the prior and does not access a paired target.']
    return b.scene

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--scene',type=Path); parser.add_argument('--output',type=Path); parser.add_argument('--rebuild-catalog',action='store_true',help='Explicitly create the original demo catalog (existing files are never overwritten)'); args=parser.parse_args()
    if args.scene:
        if args.rebuild_catalog: parser.error('--scene and --rebuild-catalog are mutually exclusive')
        scene=json.loads(args.scene.read_text()); dest=args.output or args.scene.with_suffix('.svg')
        if dest.suffix.lower() != '.svg': parser.error('--output must end in .svg')
        if dest.exists() or dest.is_symlink(): parser.error(f'Refusing to overwrite existing output: {dest}')
        svg=render_svg(scene); dest.parent.mkdir(parents=True,exist_ok=True)
        with dest.open('x') as f: f.write(svg)
        return
    if not args.rebuild_catalog: parser.error('Provide --scene and --output; demo creation requires --rebuild-catalog')
    if args.output: parser.error('--output requires --scene')
    targets=[ROOT/'components'/'catalog.json']+[ROOT/'components'/component/(f'{component}-{style}'+suffix) for component in ('ode','sde','flow-matching') for style in THEMES for suffix in ('.json','.svg')]
    existing=[str(p) for p in targets if p.exists() or p.is_symlink()]
    if existing: parser.error('Refusing to overwrite existing catalog files: '+', '.join(existing))
    entries=[]
    for factory in (ode,sde,fm):
        for style in THEMES:
            scene=factory(style); directory=ROOT/'components'/scene['component']; directory.mkdir(parents=True,exist_ok=True)
            stem=directory/scene['id']
            with stem.with_suffix('.json').open('x') as f: f.write(json.dumps(scene,ensure_ascii=False,indent=2)+'\n')
            with stem.with_suffix('.svg').open('x') as f: f.write(render_svg(scene))
            rel=lambda p: str(p.relative_to(ROOT))
            entries.append(dict(id=scene['id'],component=scene['component'],style=style,tags=[scene['component'],style,'editable','illustrative','dynamics'],scene=rel(stem.with_suffix('.json')),svg=rel(stem.with_suffix('.svg')),preview=f'output/previews/{scene["id"]}.png',license='original-project',scientific_notes=scene['scientific_notes']))
    with (ROOT/'components'/'catalog.json').open('x') as f: f.write(json.dumps(entries,ensure_ascii=False,indent=2)+'\n')
    print(f'Built {len(entries)} original editable scenes.')

if __name__=='__main__': main()
