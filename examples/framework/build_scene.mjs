#!/usr/bin/env node
// Original editable teaching diagram. No external artwork or library components.
import fs from 'node:fs/promises';
import path from 'node:path';
const args=process.argv.slice(2);
if(args.length!==2||args[0]!=='--output')throw new Error('Usage: node build_scene.mjs --output NEW.scene.json');
const destination=path.resolve(args[1]);
const C={ink:'#24344F',muted:'#67758C',blue:'#4575AA',blueLight:'#D9E8F4',violet:'#7968B0',violetLight:'#EAE5F4',coral:'#D98870',coralLight:'#F8E3DA',grid:'#E6EAF0',white:'#FFFFFF'};
const objects=[];
function add(o){objects.push(o);return o.id;}
function text(id,x,y,w,t,size=26,color=C.ink,bold=false){return add({id,type:'text',role:'label',x,y,width:w,height:size*1.4,text:t,fontFamily:'Arial',fontSize:size,fill:color,bold});}
function line(id,pts,color=C.ink,width=2.5,arrow=false,dashed=false){return add({id,type:'polyline',role:arrow?'data-flow':'line',points:pts,fill:'none',stroke:color,strokeWidth:width,endArrow:arrow,dashed});}
function box(id,x,y,w,h,fill,stroke='none',width=1.5,radius=0){return add({id,type:'rect',role:'mechanism-boundary',x,y,width:w,height:h,fill,stroke,strokeWidth:width,radius});}
function dot(id,x,y,r,color,stroke='none',sw=0){return add({id,type:'ellipse',role:'state',x:x-r,y:y-r,width:r*2,height:r*2,fill:color,stroke,strokeWidth:sw,semantic_color:true});}
function cloud(id,cx,cy,color,mode){
  for(let i=0;i<24;i++){
    const a=i*2.39996,r=8+Math.sqrt(i)*8.5;
    let dx=Math.cos(a)*r,dy=Math.sin(a)*r*.75;
    if(mode==='clusters'){dx=(i%2?29:-29)+Math.cos(a)*r*.44;dy=(i%2?-17:17)+Math.sin(a)*r*.49;}
    dot(`${id}-${i}`,cx+dx,cy+dy,3.7+(i%3)*.25,color);
  }
}
text('title',54,30,1300,'Conditional Flow Matching',38,C.ink,true);
text('train-label',54,106,200,'(a)  Training',28,C.ink,true);
text('training-subtitle',266,111,900,'Match a velocity field to paired endpoint displacements',22,C.muted);
// Endpoints feed a straight conditional path, not the eventual sampling trajectory.
cloud('noise',131,243,C.blue,'noise');
cloud('data',131,386,C.coral,'clusters');
text('noise-label',58,167,160,'Noise  x₀',24,C.blue,true);
text('data-label',58,419,180,'Data  x₁ ∣ c',24,C.coral,true);
line('noise-to-path',[[193,242],[235,242],[235,294],[287,294]],C.ink,2.5,true);
line('data-to-path',[[193,385],[235,385],[235,317],[287,317]],C.ink,2.5,true);
text('interpolation-label',302,166,390,'Sample an intermediate state',24,C.ink,true);
box('path-ground',295,213,355,184,'#F7F8FB');
for(let i=0;i<5;i++){
 const x0=327+(i%2)*15,y0=239+i*30,x1=610-(i%3)*8,y1=249+i*28,t=.48;
 line(`pair-${i}`,[[x0,y0],[x1,y1]],'#BBC5D5',1.8);
 dot(`pair-noise-${i}`,x0,y0,5.5,C.blue);dot(`pair-data-${i}`,x1,y1,5.5,C.coral);
 const xx=x0*(1-t)+x1*t, yy=y0*(1-t)+y1*t;
 dot(`intermediate-${i}`,xx,yy,6.5,C.violet,C.white,1.2);
}
text('path-equation',310,414,460,'xₜ = (1 − t)x₀ + tx₁',26,C.ink);
line('state-to-field',[[650,306],[747,306]],C.ink,2.6,true);
text('state-arrow-label',677,267,70,'xₜ',27,C.violet,true);
// The layered glyph denotes a generic learned function, not a claimed architecture.
box('velocity-network',754,214,291,185,C.violetLight,C.violet,2,14);
const layers=[[787,[264,306,348]],[846,[244,285,326,367]],[909,[244,285,326,367]],[969,[265,306,347]]];
for(let k=0;k<layers.length-1;k++)for(let i=0;i<layers[k][1].length;i++)for(let j=0;j<layers[k+1][1].length;j++)if((i+j)%2===0)line(`network-edge-${k}-${i}-${j}`,[[layers[k][0],layers[k][1][i]],[layers[k+1][0],layers[k+1][1][j]]],'#B6ACCE',1.2);
for(let k=0;k<layers.length;k++)for(let j=0;j<layers[k][1].length;j++)dot(`network-unit-${k}-${j}`,layers[k][0],layers[k][1][j],7.5,k===0?C.white:C.violet,C.violet,1.6);
text('velocity-label',775,410,350,'vθ(xₜ, t, c)',28,C.violet,true);
text('condition-label',814,164,250,'Time t, condition c',23,C.muted);
line('condition-input',[[893,201],[893,214]],C.muted,2,true,true);
line('prediction-output',[[1045,306],[1106,306]],C.ink,2.6,true);
text('predicted-label',1092,342,240,'Predicted velocity',22,C.violet);
dot('predicted-start',1138,320,4,C.violet);
line('predicted-vector',[[1138,320],[1220,284]],C.violet,4,true);
text('target-label',1100,166,260,'Target  x₁ − x₀',24,C.coral,true);
dot('target-start',1138,238,4,C.coral);
line('target-vector',[[1138,238],[1220,214]],C.coral,4,true);
box('loss-boundary',1334,227,194,114,'#F8F4F1','#DBC0B5',1.6,10);
text('loss-label',1360,247,180,'Velocity loss',24,C.ink,true);
text('loss-operator',1372,280,150,'‖vθ − uₜ‖²',26,C.ink);
line('predicted-to-loss',[[1241,305],[1334,305]],C.violet,2.3,true);
line('target-to-loss',[[1241,226],[1290,226],[1290,252],[1334,252]],C.coral,2.3,true);
text('target-definition',1097,408,445,'uₜ = x₁ − x₀',25,C.coral);
line('section-rule',[[54,483],[1544,483]],'#D4DBE5',1.5);
text('sampling-label',54,509,387,'(b)  Conditional generation',28,C.ink,true);
text('sampling-subtitle',449,514,1010,'Integrate the learned field from fresh noise',22,C.muted);
// The lower field is explicitly an illustrative learned marginal field at inference.
cloud('fresh-noise',133,733,C.blue,'noise');
text('fresh-noise-label',54,625,175,'Fresh noise',24,C.blue,true);
text('fresh-noise-math',116,800,80,'x₀',26,C.blue,true);
line('noise-to-integrator',[[196,733],[294,733]],C.ink,2.5,true);
box('sampling-domain',301,617,848,211,'#F9FAFC');
for(let i=0;i<14;i++)line(`grid-v-${i}`,[[325+i*62,628],[325+i*62,815]],C.grid,1);
for(let i=0;i<5;i++)line(`grid-h-${i}`,[[314,630+i*44],[1136,630+i*44]],C.grid,1);
// A smooth noncrossing transport family with common time and distinct initial states.
for(let i=0;i<5;i++){
 const y0=658+i*32,pts=[];
 for(let k=0;k<=70;k++){const q=k/70;pts.push([337+774*q,y0+22*Math.sin(Math.PI*q)*(i-2)/2+12*Math.sin(2*Math.PI*q)]);}
 line(`sample-trajectory-${i}`,pts,i===2?C.violet:'#ACA0C8',i===2?3.8:2.4,false);
 dot(`initial-state-${i}`,337,y0,5.5,C.blue);dot(`final-state-${i}`,1111,y0,5.5,C.coral);
 const m=42;line(`trajectory-direction-${i}`,[pts[m],pts[m+2]],i===2?C.violet:'#ACA0C8',i===2?3.8:2.4,true);
}
// Quiver arrows are schematic, carry no measured magnitude and stay behind labels.
for(let i=0;i<12;i++)for(let j=0;j<4;j++){
 const x=370+i*61,y=638+j*48,q=(x-337)/774,dy=(22*Math.PI*Math.cos(Math.PI*q)*(j-1.5)/2+24*Math.PI*Math.cos(2*Math.PI*q))/774;
 line(`field-arrow-${i}-${j}`,[[x,y],[x+19,y+dy*19]],'#A8B6C9',1.2,true);
}
text('integration-equation',492,570,670,'dxₜ / dt = vθ(xₜ, t, c)',28,C.violet,true);
text('learned-parameter-label',1041,567,180,'learned θ',20,C.muted);
line('parameter-transfer',[[1022,399],[1022,617]],C.muted,1.7,true,true);
text('generation-condition',318,570,190,'Condition c',23,C.muted);
line('generation-condition-input',[[400,604],[400,617]],C.muted,1.8,true,true);
text('integration-label',558,843,500,'Integrate from t = 0 to t = 1',23,C.muted);
line('integrator-to-output',[[1149,733],[1255,733]],C.ink,2.6,true);
cloud('generated-samples',1377,734,C.coral,'clusters');
text('samples-title',1255,625,285,'Conditional samples',24,C.coral,true);
text('samples-math',1302,800,255,'x₁ ∼ pθ(x ∣ c)',25,C.coral);
text('schematic-disclosure',54,907,1450,'Teaching schematic. Point locations and field arrows illustrate the mechanism, not experimental results.',19,C.muted);
const scene={schema_version:1,id:'conditional-flow',component:'conditional-flow-training-inference-framework',style:'modern',width:1600,height:950,scientific_notes:[
 'Original teaching schematic authored for Astra Figure Workflow. All artwork consists of native editable shapes.',
 'Sources: Lipman et al., Flow Matching for Generative Modeling, ICLR 2023, https://arxiv.org/abs/2210.02747 ; Tong et al., Improving and Generalizing Flow-Based Generative Models with Minibatch Optimal Transport, https://arxiv.org/abs/2302.00482 .',
 'Specification: choose x0 from a base distribution independently of a condition-data pair (c,x1); t is uniform on [0,1]; xt=(1-t)x0+t*x1, ut=x1-x0. Fit vtheta(xt,t,c) with expected squared velocity error. At inference integrate dxt/dt=vtheta(xt,t,c) from a fresh x0.',
 'The top paths are conditional training interpolants. The bottom curves illustrate learned marginal sampling trajectories and need not be straight. No SDE, minibatch optimal transport pairing, neural architecture, particular numerical solver, empirical distribution fit or experiment is claimed.',
 'Network units denote an abstract learned function, not a specified layer count. Schematic points, arrow lengths, curves and colors are illustrative rather than measured.',
 'Color key: blue = base/noise states; coral = data endpoint/target or generated endpoint states; violet = intermediate state and learned velocity function. Dashed arrows = conditioning or transfer of learned parameters, not additional samples.'
],objects};
await fs.mkdir(path.dirname(destination),{recursive:true});
await fs.writeFile(destination,JSON.stringify(scene,null,2)+'\n',{flag:'wx'});
console.log(`Wrote ${objects.length} editable objects`);
