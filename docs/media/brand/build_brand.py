"""Rebuild self-contained SVG art. Requires fonttools; previews are optional."""
from pathlib import Path
from html import escape
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen

ROOT = Path(__file__).resolve().parent
FONT = TTFont(ROOT / 'fonts/ComicNeue-Bold.ttf')
GLYPHS = FONT.getGlyphSet()
CMAP = FONT.getBestCmap()
UNITS = FONT['head'].unitsPerEm
INK, BLUE, PALE, CREAM, CORAL = '#31566A', '#5BA6C2', '#EAF5F8', '#FFF1D7', '#E98B79'


def lettering(s, x, baseline, size, fill=INK):
    scale = size / UNITS
    parts = []
    for ch in s:
        glyph_name = CMAP[ord(ch)]
        pen = SVGPathPen(GLYPHS)
        GLYPHS[glyph_name].draw(pen)
        if pen.getCommands():
            parts.append(f'<path d="{pen.getCommands()}" transform="translate({x:.3f} {baseline}) scale({scale:.6f} {-scale:.6f})" fill="{fill}"/>')
        x += FONT['hmtx'][glyph_name][0] * scale
    return ''.join(parts), x


def svg(name, w, h, title, content):
    (ROOT / name).write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-labelledby="title"><title id="title">{escape(title)}</title>{content}</svg>\n')


def snow(x, y, size, color=BLUE):
    return f'<g transform="translate({x} {y})" fill="none" stroke="{color}" stroke-width="2.5" stroke-linecap="round"><path d="M{-size} 0H{size} M0 {-size}V{size} M{-size*.7} {-size*.7}L{size*.7} {size*.7} M{-size*.7} {size*.7}L{size*.7} {-size*.7}"/></g>'


def badge_icon(kind):
    common = f'fill="none" stroke="{INK}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"'
    shapes = {
        'demo': f'<rect x="8" y="8" width="23" height="21" rx="5" fill="{CREAM}"/><path d="M10 23l6-6 5 4 8-10"/><circle cx="16" cy="12" r="2" fill="{CORAL}" stroke="none"/><path d="M25 8h6v6"/>',
        'materials': f'<path d="M7 14V9a3 3 0 013-3h7l4 4h10a3 3 0 013 3v15H9a3 3 0 01-3-4l3-10z" fill="{CREAM}"/><path d="M9 14h25l-3 14H9" fill="{PALE}"/><path d="M17 20h9"/>',
        'spatial': f'<path d="M20 4L33 12V27L20 34 7 27V12Z" fill="{PALE}"/><path d="M7 12l13 8 13-8M20 20v14"/><path d="M20 4v16" stroke-dasharray="2 4"/><path d="M10 12l10-5 10 5-10 5z" fill="{CREAM}" stroke="none"/>',
        'start': f'<path d="M12 24C12 11 24 4 32 5c1 9-6 21-19 22z" fill="{CREAM}"/><path d="M13 16l-7 2-1 9 9-4M22 25l-2 9 9-2 1-11" fill="{CORAL}"/><circle cx="25" cy="12" r="3.2" fill="{PALE}"/><path d="M8 30l-3 4M12 32l-2 4" stroke="{BLUE}"/>',
        'edit': f'<path d="M7 13V7h6M25 7h6v6M31 25v6h-6M13 31H7v-6" stroke-dasharray="3 2"/><path d="M13 23l2-7L26 5l6 6-11 11z" fill="{CREAM}"/><path d="M15 16l6 6M24 7l6 6"/><path d="M13 23l5-1-4-4z" fill="{INK}" stroke="none"/>',
    }
    return f'<g {common}>{shapes[kind]}</g>'


# A lightweight snowy paper strip, with enough visual weight for a repository title.
header = f'''<path d="M18 77Q20 28 78 32L916 26Q975 24 980 78L980 116Q979 160 921 162L75 166Q18 164 18 117Z" fill="{PALE}"/>
<path d="M621 34Q680 9 752 32L909 27Q946 26 960 52L934 64 686 70Z" fill="{CREAM}"/>
<path d="M20 110Q15 67 38 44M955 142q24-12 23-35" fill="none" stroke="#9CCDDD" stroke-width="3" stroke-linecap="round"/>
<g transform="translate(88 49) rotate(-9 40 48)">
<path d="M3 9Q1 3 10 3h52l17 17v69q0 9-9 9H10q-7 0-7-8Z" fill="#fff" stroke="{INK}" stroke-width="3.2" stroke-linejoin="round"/>
<path d="M62 3v17h17" fill="{CREAM}" stroke="{INK}" stroke-width="3.2" stroke-linejoin="round"/>
<path d="M19 29h25M19 40h40M19 51h30" stroke="#9CCDDD" stroke-width="3.2" stroke-linecap="round"/>
<path d="M20 76q14-29 28-11t26-7" fill="none" stroke="{BLUE}" stroke-width="4.5" stroke-linecap="round"/>
<path d="M49 83l9-25 41-31q5-3 10 3t1 10L67 71Z" fill="{CREAM}" stroke="{INK}" stroke-width="3" stroke-linejoin="round"/>
<path d="M58 58l9 13M93 32l11 10" stroke="{INK}" stroke-width="3"/>
<path d="M49 83l5-13 8 7Z" fill="{INK}"/>
<path d="M99 27q5-3 10 3t1 10l-6 3-11-11Z" fill="{CORAL}" stroke="{INK}" stroke-width="3"/>
</g>'''
txt1, end = lettering('Astra', 243, 132, 127)
txt2, end = lettering('Draw', end + 3, 132, 127, BLUE)
header += txt1 + txt2
header += f'<path d="M248 150Q486 162 752 149" fill="none" stroke="{CORAL}" stroke-width="4.5" stroke-linecap="round"/><path d="M786 153q23-7 39-4" fill="none" stroke="{INK}" stroke-width="2.5" stroke-linecap="round"/>'
header += snow(866, 67, 13) + snow(205, 48, 7)
header += f'<circle cx="897" cy="123" r="5" fill="{CORAL}"/><circle cx="838" cy="44" r="3" fill="{BLUE}"/><path d="M931 76l7-11M937 86l11-2" stroke="{INK}" stroke-width="2.5" stroke-linecap="round"/>'
svg('wordmark.svg', 1000, 190, 'AstraDraw — research figures, your way', header)

navs = [('demo', 'Demos', 153), ('materials', 'Materials', 163), ('spatial', '2D / 3D', 153), ('start', 'Start here', 166), ('edit', 'Local edits', 176)]
for i, (kind, label, width) in enumerate(navs):
    bg = CREAM if kind in ('demo', 'start') else PALE
    content = f'<rect x="2" y="5" width="{width-4}" height="42" rx="16" fill="#C9DFE7"/><rect x="2" y="2" width="{width-4}" height="42" rx="16" fill="{bg}" stroke="{INK}" stroke-width="1.6"/>'
    content += f'<g transform="translate(9 4) scale(.9)">{badge_icon(kind)}</g>'
    paths, end = lettering(label, 48, 30, 22)
    content += paths
    svg('nav-'+kind+'.svg', width, 50, label, content)

divider = f'<path d="M18 31Q136 13 247 29T461 29M540 29Q652 13 764 29T982 25" fill="none" stroke="#B9DCE7" stroke-width="2.2" stroke-linecap="round"/>'
divider += snow(500, 28, 11)
divider += f'<circle cx="472" cy="28" r="2.5" fill="{CORAL}"/><circle cx="528" cy="28" r="2.5" fill="{CORAL}"/>'
svg('divider.svg', 1000, 56, 'Snowy section divider', divider)

def line_width(s, size):
    return sum(FONT['hmtx'][CMAP[ord(c)]][0] for c in s) * size / UNITS

top = 'Your paper. Your references.'
bottom = 'Draw it with Astra.'
tagline, _ = lettering(top, (900-line_width(top, 33))/2, 36, 33)
second, _ = lettering(bottom, (900-line_width(bottom, 39))/2, 84, 39, BLUE)
tagline += second
tagline += f'<path d="M252 72l-17-6m15 16-18 2M648 72l17-6m-15 16 18 2" stroke="{CORAL}" stroke-width="2.6" stroke-linecap="round" fill="none"/>'
svg('tagline.svg', 900, 103, 'Your paper. Your references. Draw it with Astra.', tagline)
