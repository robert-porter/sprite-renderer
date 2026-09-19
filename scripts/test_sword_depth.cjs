// Check page addressing and playback stalls using the real preview implementations.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const SpritePlayer=require('./player.js');
require('./sword-depth.js');
const clip={frameCount:4,fps:4,duration:1,loop:true,baseClip:'swing',
  frames:[0,1,2,3].map(i=>({x:i%2*16,y:0,w:16,h:16,page:Math.floor(i/2)})),
  pages:[{sheetSize:[32,16]},{sheetSize:[32,16]}],layers:{}};
for(const layer of ['character','steel'])clip.layers[layer]={pages:[0,1].map(i=>({color:`${layer}-${i}.png`,depth:`${layer}-${i}-z.png`}))};
const lab=Object.create(globalThis.SwordDepthPreview.prototype);
Object.assign(lab,{spec:{animations:{swing:clip}},picker:{value:'steel'},view:{value:'0'},animation:{},status:{},canvas:{width:16,height:16},rect:'rect',mode:'mode'});
const loaded=new Set(),requests=[];
lab.texture=(url,wanted)=>{requests.push({url,wanted});return {ready:loaded.has(url),texture:url};};
assert.deepEqual(lab.urls('swing',2),['character-1.png','character-1-z.png','steel-1.png','steel-1-z.png']);
assert.equal(lab.readyAt('swing',2),false);
lab.urls('swing',2).forEach(url=>loaded.add(url));
assert.equal(lab.readyAt('swing',2),true);
let coords,draws=0;
lab.gl={TEXTURE0:0,TEXTURE_2D:1,TRIANGLES:2,activeTexture(){},bindTexture(){},uniform4f(...args){coords=args;},uniform1i(){},viewport(){},drawArrays(){draws++;}};
assert.equal(lab.frame('swing',3),lab.canvas);
assert.deepEqual(coords,['rect',.5,0,.5,1], 'Frame 4 uses page 2 local rectangle');
lab.frame('swing',3);assert.equal(draws,1,'Paused frame is reused');
lab.view.value='2';lab.frame('swing',3);assert.equal(draws,2,'Changing inspection mode redraws');
lab.picker.value='none';assert.deepEqual(lab.urls('swing',2),[]);assert.equal(lab.frame('swing',2),null);
lab.picker.value='steel';assert.equal(lab.frame('unsupported',0),null);

clip.layers.steel.trail={pages:[0,1].map(i=>({color:`trail-${i}.png`,depth:`trail-${i}-z.png`}))};
lab.trail={value:'on'};
assert.equal(lab.urls('swing',2).length,6,'Enabled slash requests matching color and depth');
assert.equal(lab.readyAt('swing',2),false,'Missing slash page holds playback despite loaded body and sword');
lab.urls('swing',2).forEach(url=>loaded.add(url));
assert.equal(lab.readyAt('swing',2),true);
lab.frame('swing',3);const withTrailDraws=draws;
lab.trail.value='off';lab.frame('swing',3);
assert.equal(draws,withTrailDraws+1,'Toggling slash off redraws a paused frame');
assert.equal(lab.urls('swing',2).length,4,'Disabled slash needs no effect textures');
delete clip.layers.steel.trail;lab.trail.value='on';
assert.equal(lab.urls('swing',2).length,4,'Unsupported attack falls back to body and sword');
lab.picker.value='none';assert.deepEqual(lab.urls('swing',2),[]);lab.picker.value='steel';
console.log('PASS slash page readiness, paused toggle, unsupported clips and unequipped fallback');

const html=fs.readFileSync(__dirname+'/preview.html','utf8');
const tick=html.slice(html.indexOf('function tick(now)'),html.indexOf('library();loading();requestAnimationFrame(tick);'));
const player=new SpritePlayer({swing:clip},'swing');
player.time=.45;
let ready=false;
const state={textContent:''};
const context=vm.createContext({last:0,player,clips:{swing:clip},images:new Map([['swing',{complete:true,naturalWidth:32}]]),
  prepareImages(){},nextClip(){return null;},sync(){},draw(){},requestAnimationFrame(){},
  $:id=>id==='speed'?{value:1}:state,swordLab:{readyAt(name,index){return index<2||ready;}}});
vm.runInContext(tick,context);
vm.runInContext('tick(100)',context);
assert.equal(player.time,.45,'Missing next page holds the current pose');
assert.equal(state.textContent,'Loading sword layers…');
ready=true;vm.runInContext('tick(200)',context);
assert.equal(player.frameIndex,2,'Playback enters the next page when ready');
player.seek(3);vm.runInContext('tick(300)',context);
assert.equal(player.frameIndex,3);assert.equal(player.playing,false,'Paused seeking stays paused');
console.log('PASS sword texture pages, local atlas rectangles, inspection redraw, unsupported clips, boundary loading and paused seek');
const manifestPath=path.join(__dirname,'../output/universal/sword-lab/swords.json');
if(fs.existsSync(manifestPath)){
 const real=JSON.parse(fs.readFileSync(manifestPath,'utf8'));
 const catalog=JSON.parse(fs.readFileSync(path.join(__dirname,'../output/universal/review-sprites.json'),'utf8')).animations;
 for(const name of ['idle','idle_open35_head35','sword_idle','sword_idle_edited','ual2_sword_regular_combo','ual2_sword_regular_combo_edited','ual2_sword_heavy_combo','ual2_sword_heavy_combo_edited']){
  const clip=real.animations[name];assert.ok(clip,'Equipped sword must remain supported: '+name);
  assert.deepEqual(clip.sourceFrames,catalog[name].sourceFrames);
  assert.equal(clip.frameCount,catalog[name].frameCount);
  for(const layer of Object.values(clip.layers))for(const page of layer.pages){
   for(const key of ['color','depth'])assert.ok(fs.existsSync(path.join(__dirname,'../output/universal',page[key])));
  }
 }
 console.log('PASS equipped neutral/sword idle and both combo presets in Base and Edited modes');
}
