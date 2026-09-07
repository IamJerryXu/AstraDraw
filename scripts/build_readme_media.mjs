#!/usr/bin/env node
/** Build a labeled vector close-up of the real before/after demo exports. */
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const read=async name=>fs.readFile(path.join(root,'output/showcase',name),'utf8');
const content=svg=>svg.replace(/^<svg\b[^>]*>/,'').replace(/<\/svg>\s*$/,'');
const before=content(await read('manifold.svg'));
const after=content(await read('manifold-edited.svg'));
const scene=JSON.parse(await fs.readFile(path.join(root,'examples/showcase/manifold.scene.json'),'utf8'));
const edited=JSON.parse(await fs.readFile(path.join(root,'examples/showcase/manifold-edited.scene.json'),'utf8'));
const a=scene.objects.find(o=>o.id==='surface-target-label');
const b=edited.objects.find(o=>o.id===a.id);
if(!a||!b||b.y-a.y!==8)throw Error('Expected the documented 8 px label edit');
if(scene.objects.some(o=>o.id!==a.id&&JSON.stringify(o)!==JSON.stringify(edited.objects.find(e=>e.id===o.id))))throw Error('Unexpected edits outside the target label');
const panel=(body,x,y,id)=>`<svg x="${x}" y="84" width="444" height="370" viewBox="915 94 240 200">${body.replace(/id="([^"]+)"/g,`id="${id}-$1"`)}<rect x="963" y="${y+2}" width="76" height="53" rx="4" fill="none" stroke="#A45D64" stroke-width="1.3" stroke-dasharray="4 3"/></svg>`;
const svg=`<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="516" viewBox="0 0 1000 516" role="img" aria-labelledby="title desc">
<title id="title">Selected-object refinement: before and after</title>
<desc id="desc">Close-ups of the actual vector scenes. The p1 label moves down by 8 pixels. Dashed outlines identify the selected label and are added for this comparison.</desc>
<rect width="1000" height="516" rx="14" fill="#F6F8FA"/>
<g font-family="Arial, Helvetica, sans-serif"><text x="38" y="43" font-size="17" font-weight="700" letter-spacing="1.5" fill="#586D77">BEFORE</text><text x="526" y="43" font-size="17" font-weight="700" letter-spacing="1.5" fill="#A45D64">AFTER</text><text x="526" y="68" font-size="16" fill="#586D77">Selected label: down 8 px</text></g>
<rect x="26" y="79" width="460" height="380" rx="7" fill="white"/>
<rect x="514" y="79" width="460" height="380" rx="7" fill="white"/>
${panel(before,34,a.y,'before')}${panel(after,522,b.y,'after')}
<text x="500" y="491" text-anchor="middle" font-family="Arial, Helvetica, sans-serif" font-size="17" fill="#253640">The surface, samples and paths stay unchanged.</text>
</svg>`;
await fs.mkdir(path.join(root,'docs/media'),{recursive:true});
await fs.writeFile(path.join(root,'docs/media/selection-detail.svg'),svg);
console.log('Built docs/media/selection-detail.svg from the two source scenes.');
