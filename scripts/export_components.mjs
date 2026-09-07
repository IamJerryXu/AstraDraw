#!/usr/bin/env node
/** Native-editable scene exporter. Final files and sidecars are never overwritten. */
import fs from 'node:fs/promises';
import {constants} from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import {createHash} from 'node:crypto';
import {createRequire} from 'node:module';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {execFileSync} from 'node:child_process';

const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const sha256=bytes=>createHash('sha256').update(bytes).digest('hex');
export const lineStyle=o=>o.dotted?'dotted':o.dashed?'dashed':'solid';
export const needsArrow=(o,ids)=>!!o.endArrow&&!ids.has(o.id+'--arrow');

export function imageSource(o){
  const match=typeof o.src==='string'&&o.src.match(/^data:(image\/(?:png|jpeg));base64,([A-Za-z0-9+/]+={0,2})$/);
  if(!match)throw Error('Image src must be an embedded PNG/JPEG data URI: '+o.id);
  const bytes=Buffer.from(match[2],'base64');
  if(bytes.toString('base64')!==match[2]||!(match[1]==='image/png'?bytes.subarray(0,8).equals(Buffer.from('89504e470d0a1a0a','hex')):bytes[0]===255&&bytes[1]===216&&bytes.at(-2)===255&&bytes.at(-1)===217))throw Error('Invalid image bytes: '+o.id);
  if(o.src_sha256!==undefined&&o.src_sha256!==sha256(bytes))throw Error('Image source hash mismatch: '+o.id);
  if(['x','y','width','height'].some(k=>!Number.isFinite(o[k]))||o.width<=0||o.height<=0)throw Error('Invalid image frame: '+o.id);
  if(o.fit!==undefined&&o.fit!=='contain')throw Error('Image fit must preserve the complete source: '+o.id);
  return {bytes,contentType:match[1],sha256:sha256(bytes)};
}

export function parseArguments(args){
  const result={scenes:[],output:path.join(ROOT,'output/components.pptx')};
  for(let i=0;i<args.length;i++){
    const flag=args[i];
    if(flag==='--help'){result.help=true;continue;}
    if(!['--scene','--output','--build-dir'].includes(flag))throw Error('Unknown argument: '+flag);
    const value=args[++i];
    if(!value||value.startsWith('--'))throw Error('Missing value for '+flag);
    if(flag==='--scene')result.scenes.push(path.resolve(value));
    else if(flag==='--output')result.output=path.resolve(value);
    else result.buildDir=path.resolve(value);
  }
  if(!/\.pptx$/i.test(result.output))throw Error('--output must end in .pptx');
  return result;
}

async function assertAbsent(target){
  try{await fs.lstat(target);}catch(e){if(e.code==='ENOENT')return;throw e;}
  throw Error('Refusing to overwrite existing output or sidecar: '+target);
}

export async function preflight(options){
  const sources=options.scenes.length?options.scenes:JSON.parse(await fs.readFile(path.join(ROOT,'components/catalog.json'),'utf8')).map(x=>path.join(ROOT,x.scene));
  const bytes=await Promise.all(sources.map(p=>fs.readFile(p)));
  const scenes=bytes.map(b=>JSON.parse(b.toString('utf8')));
  if(!scenes.length)throw Error('At least one scene is required');
  const sceneIds=new Set();
  for(const scene of scenes){
    if(!/^[A-Za-z0-9][A-Za-z0-9._-]*$/.test(scene.id)||sceneIds.has(scene.id))throw Error('Scene IDs must be unique safe filenames: '+scene.id);
    sceneIds.add(scene.id);
    if(!Number.isFinite(scene.width)||scene.width<=0||!Number.isFinite(scene.height)||scene.height<=0)throw Error('Invalid canvas: '+scene.id);
    if(scene.width!==scenes[0].width||scene.height!==scenes[0].height)throw Error('Mixed canvas sizes are not supported.');
    if(!Array.isArray(scene.objects)||!scene.objects.length)throw Error('Scene has no objects: '+scene.id);
    const ids=new Set();
    for(const o of scene.objects){
      if(typeof o.id!=='string'||!o.id||ids.has(o.id))throw Error('Duplicate or missing object ID: '+o.id);
      ids.add(o.id);
      if(!['text','rect','ellipse','polyline','image'].includes(o.type))throw Error('Unsupported object type: '+o.type);
      if(o.type==='image')imageSource(o);
      if(o.type==='polyline'&&(!Array.isArray(o.points)||o.points.length<2||o.points.some(p=>p.length!==2||p.some(n=>!Number.isFinite(n)))))throw Error('Invalid polyline: '+o.id);
    }
  }
  const output=options.output,stem=output.replace(/\.pptx$/i,'');
  const mapPath=stem+'.object-map.json',previewDir=stem+'-previews';
  // Reject legacy report names too, to avoid pairing this export with stale reports.
  await Promise.all([output,mapPath,previewDir,stem+'.validation.json'].map(assertAbsent));
  return {scenes,sources,sourceHashes:bytes.map(sha256),output,mapPath,previewDir};
}

export async function main(args=process.argv.slice(2)){
  const options=parseArguments(args);
  if(options.help){console.log('Usage: export_components.mjs [--scene file.json ...] --output new.pptx [--build-dir private-directory]\nOmit --scene to export the original demo catalog. Existing outputs and sidecars are always rejected.');return;}
  const {scenes,sources,sourceHashes,output,mapPath,previewDir}=await preflight(options);
  const cache=path.join(os.homedir(),'.cache/codex-runtimes/codex-primary-runtime/dependencies');
  const modules=process.env.RUNTIME_NODE_MODULES||path.join(cache,'node/node_modules');
  process.env.RUNTIME_NODE_MODULES=modules;
  process.env.RUNTIME_NODE ||= path.join(cache,'node/bin/node');
  const python=process.env.RUNTIME_PYTHON||path.join(cache,'python/bin/python3');
  const runtimeRequire=createRequire(path.join(modules,'../package.json'));
  const {Presentation,PresentationFile,FileBlob}=await import(pathToFileURL(runtimeRequire.resolve('@oai/artifact-tool')).href);
  let skill=process.env.PRESENTATIONS_SKILL_DIR;
  if(!skill){
    const base=path.join(os.homedir(),'.codex/plugins/cache/openai-primary-runtime/presentations');
    const versions=(await fs.readdir(base)).sort((a,b)=>b.localeCompare(a,undefined,{numeric:true}));
    skill=path.join(base,versions[0],'skills/presentations');
  }
  const {finalizePresentation}=await import(pathToFileURL(path.join(skill,'container_tools/artifact_tool_utils.mjs')).href);
  const buildRoot=options.buildDir||path.join(ROOT,'.local/build');
  const buildFromOutput=path.relative(path.dirname(output),buildRoot);
  if(!buildFromOutput||(!buildFromOutput.startsWith('..'+path.sep)&&!path.isAbsolute(buildFromOutput)))throw Error('--build-dir must be separate from the output directory');
  const buildFromRoot=path.relative(ROOT,buildRoot);
  if(buildFromRoot==='..'||buildFromRoot.startsWith('..'+path.sep)||path.isAbsolute(buildFromRoot))throw Error('--build-dir must be inside the workspace');
  await fs.mkdir(buildRoot,{recursive:true});
  const build=await fs.mkdtemp(path.join(buildRoot,'export-'));
  await fs.mkdir(path.join(build,'final'));
  const stagedPreviews=path.join(build,'previews');await fs.mkdir(stagedPreviews);
  const presentation=Presentation.create({slideSize:{width:scenes[0].width,height:scenes[0].height}});
  const mapping=[];
  function poly(slide,id,points,fill,stroke,width,style,closed){
    const xs=points.map(p=>p[0]),ys=points.map(p=>p[1]),x=Math.min(...xs),y=Math.min(...ys),w=Math.max(.01,Math.max(...xs)-x),h=Math.max(.01,Math.max(...ys)-y);
    return slide.shapes.add({geometry:'custom',name:id,position:{left:x,top:y,width:w,height:h},fill:fill||'none',line:{fill:stroke,width,style},customPaths:[{width:w,height:h,commands:[{moveTo:{x:points[0][0]-x,y:points[0][1]-y}},...points.slice(1).map(p=>({lineTo:{x:p[0]-x,y:p[1]-y}})),...(closed?[{close:{}}]:[])]}]});
  }
  for(const [index,scene] of scenes.entries()){
    const slide=presentation.slides.add();slide.background.fill='#FFFFFF';
    const records=[],ids=new Set(scene.objects.map(o=>o.id));
    for(const o of scene.objects){
      let shape;
      if(o.type==='image'){
        const source=imageSource(o);
        shape=slide.images.add({blob:source.bytes,contentType:source.contentType,alt:o.id,fit:'contain',position:{left:o.x,top:o.y,width:o.width,height:o.height}});
        shape.lockAspectRatio=true;
      }else if(o.type==='text'){
        shape=slide.shapes.add({geometry:'textbox',name:o.id,position:{left:o.x,top:o.y,width:o.width,height:o.height},fill:'none',line:{fill:'none',width:0}});
        shape.text=o.text;shape.text.style={typeface:o.fontFamily,fontSize:o.fontSize,bold:!!o.bold,italic:!!o.italic,color:o.fill,alignment:'left',verticalAlignment:'middle',autoFit:'none',wrap:'none',insets:{left:0,right:0,top:0,bottom:0}};
      }else if(o.type==='rect'||o.type==='ellipse'){
        if(o.type==='rect'&&o.radius){
          const pts=[],r=Math.min(o.radius,o.width/2,o.height/2);
          for(const [cx,cy,a] of [[o.x+o.width-r,o.y+r,-Math.PI/2],[o.x+o.width-r,o.y+o.height-r,0],[o.x+r,o.y+o.height-r,Math.PI/2],[o.x+r,o.y+r,Math.PI]])for(let j=0;j<=12;j++)pts.push([cx+r*Math.cos(a+j*Math.PI/24),cy+r*Math.sin(a+j*Math.PI/24)]);
          shape=poly(slide,o.id,pts,o.fill,o.stroke,o.strokeWidth,lineStyle(o),true);
        }else shape=slide.shapes.add({geometry:o.type==='ellipse'?'ellipse':'rect',name:o.id,position:{left:o.x,top:o.y,width:o.width,height:o.height},fill:o.fill,line:{fill:o.stroke,width:o.strokeWidth,style:lineStyle(o)}});
      }else{
        shape=poly(slide,o.id,o.points,o.fill,o.stroke,o.strokeWidth,lineStyle(o),o.closed);
        if(needsArrow(o,ids)){
          const [a,b]=o.points.slice(-2),theta=Math.atan2(b[1]-a[1],b[0]-a[0]),len=10+o.strokeWidth,wing=len*.43;
          const q=[b,[b[0]-len*Math.cos(theta)+wing*Math.sin(theta),b[1]-len*Math.sin(theta)-wing*Math.cos(theta)],[b[0]-len*Math.cos(theta)-wing*Math.sin(theta),b[1]-len*Math.sin(theta)+wing*Math.cos(theta)]];
          const head=poly(slide,o.id+'--arrow',q,o.stroke,'none',0,'solid',true);
          records.push({scene_object_id:o.id,part:'arrowhead',pptx_shape_name:o.id+'--arrow',artifact_object_id:head.id});
        }
      }
      records.push({scene_object_id:o.id,pptx_shape_name:o.id,artifact_object_id:shape.id,object_type:o.type,role:o.role,group:o.group||null,...(o.type==='image'?{src_sha256:imageSource(o).sha256,provenance:o.provenance??null}: {})});
    }
    slide.speakerNotes.textFrame.setText((scene.scientific_notes||[]).join('\n'));
    mapping.push({scene_id:scene.id,slide_id:slide.id,objects:records,source_scene_path:sources[index],scene_sha256:sourceHashes[index]});
  }
  let candidate=path.join(build,'candidate.pptx');
  await (await PresentationFile.exportPptx(presentation)).save(candidate);
  // This runtime omits image names/alt during PPTX export. Bind picture order only
  // after independently verifying the embedded bytes and contained frame.
  if(scenes.some(s=>s.objects.some(o=>o.type==='image'))){
    const namedCandidate=path.join(build,'candidate-named.pptx');
    execFileSync(python,[path.join(ROOT,'scripts/bind_picture_names.py'),candidate,namedCandidate,JSON.stringify(scenes.map(s=>s.objects.filter(o=>o.type==='image').map(o=>({id:o.id,alt:o.alt||o.id,sha256:imageSource(o).sha256,x:o.x,y:o.y,width:o.width,height:o.height}))))]);
    candidate=namedCandidate;
  }
  const final=path.join(build,'final',path.basename(output));
  const result=await finalizePresentation({workspaceDir:ROOT,candidatePath:candidate,finalPath:final,pythonExecutable:python,integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),layoutArgs:['--expected-slide-size-emu',`${Math.round(scenes[0].width*9525)},${Math.round(scenes[0].height*9525)}`],explicitTotalSlideCount:scenes.length,requiredNativeTableOwnerSlides:[],requiredNativeChartOwnerSlides:[],fontPolicy:{basis:'design',families:[...new Set(scenes.flatMap(s=>s.objects.filter(o=>o.type==='text').map(o=>o.fontFamily)))]},verifyArtifactToolImport:true,receiptPath:path.join(build,'validation.json')});
  const finalPresentation=await PresentationFile.importPptx(await FileBlob.load(final));
  for(let i=0;i<scenes.length;i++){
    const slide=finalPresentation.slides.items[i];
    const blob=await finalPresentation.export({slide,format:'png',scale:1});
    await fs.writeFile(path.join(stagedPreviews,scenes[i].id+'.png'),new Uint8Array(await blob.arrayBuffer()),{flag:'wx'});
    const layout=await slide.export({format:'layout'});
    await fs.writeFile(path.join(build,scenes[i].id+'.layout.json'),await layout.text(),{flag:'wx'});
  }
  // Read stable names and actual IDs from the exact finalized bytes to be delivered.
  const nativeIds=JSON.parse(execFileSync(python,['-c',
    'import json,sys,zipfile,xml.etree.ElementTree as E; z=zipfile.ZipFile(sys.argv[1]); ns={"p":"http://schemas.openxmlformats.org/presentationml/2006/main"}; names=sorted([n for n in z.namelist() if n.startswith("ppt/slides/slide") and n.endswith(".xml")],key=lambda n:int(n.split("slide")[-1].split(".")[0])); print(json.dumps([{e.get("name"):e.get("id") for e in E.fromstring(z.read(n)).findall(".//p:cNvPr",ns)} for n in names]))',final],{encoding:'utf8'}));
  const pptxHash=sha256(await fs.readFile(final));
  mapping.forEach((s,i)=>{s.slide_number=i+1;s.pptx_sha256=pptxHash;s.objects.forEach(o=>{o.pptx_shape_id=nativeIds[i][o.pptx_shape_name];if(!o.pptx_shape_id)throw Error('Final PPTX lost object '+o.pptx_shape_name);});});
  const stagedMap=path.join(build,'object-map.json');await fs.writeFile(stagedMap,JSON.stringify(mapping,null,2),{flag:'wx'});
  // Recheck immediately before publication. Exclusive writes also protect against races.
  await Promise.all([output,mapPath,previewDir].map(assertAbsent));
  await fs.mkdir(path.dirname(output),{recursive:true});
  await fs.mkdir(previewDir);
  for(const s of scenes)await fs.copyFile(path.join(stagedPreviews,s.id+'.png'),path.join(previewDir,s.id+'.png'),constants.COPYFILE_EXCL);
  await fs.copyFile(stagedMap,mapPath,constants.COPYFILE_EXCL);
  await fs.copyFile(final,output,constants.COPYFILE_EXCL);
  console.log(JSON.stringify({output,mapPath,previewDir,build,slides:scenes.length,pptx_sha256:pptxHash,result},null,2));
}

if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
  main().catch(error=>{console.error(error.message);process.exitCode=1;});
}
