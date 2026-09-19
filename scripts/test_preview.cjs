const assert = require('node:assert/strict');
const SpritePlayer = require('./player.js');
const fs = require('node:fs');
const path = require('node:path');
const fixture = (duration, count, loop) => ({duration, frameCount:count, fps:count/duration, loop});
const clips = {idle:fixture(2.5,15,true), walk:fixture(1,12,true), hit:fixture(.5,6,false), land:fixture(.25,3,false)};
let p = new SpritePlayer(clips,'idle');
p.advance(-.1);assert.equal(p.frameIndex,0);
p.advance(.5);assert.equal(p.frameIndex,3);
p.toggle();p.advance(10);assert.equal(p.time,.5);p.toggle();
p.select('walk',true);p.advance(1.9);assert.equal(p.name,'idle');p.advance(.2);assert.equal(p.name,'walk');assert.ok(Math.abs(p.time-.1)<1e-8);
p.select('hit');p.advance(1);assert.equal(p.frameIndex,5);assert.equal(p.finished,true);assert.equal(p.playing,false);
p.select('walk',true);assert.equal(p.name,'walk','Switch from a completed one-shot is immediate');
p.select('hit');p.repeatClip=true;p.advance(.6);assert.equal(p.finished,false);assert.equal(p.frameIndex,1);
p.playSequence(['idle','hit','land'],false);p.advance(3.4);assert.equal(p.name,'land');assert.equal(p.frameIndex,2);assert.equal(p.finished,true);
p.playSequence(['hit','land'],true);p.advance(.8);assert.equal(p.name,'hit');assert.ok(Math.abs(p.time-.05)<1e-8);
p.seek(2);assert.equal(p.frameIndex,2);assert.equal(p.sequence,null);assert.equal(p.playing,false);
p.select('walk');assert.equal(p.frameIndex,0);assert.equal(p.playing,true);
assert.throws(()=>p.select('missing'),/Unknown/);
// Validate the real catalog and every referenced preset once renders exist.
const manifest=JSON.parse(fs.readFileSync(path.join(__dirname,'../output/universal/sprites.json'),'utf8'));
if(Object.keys(manifest.animations).length===42){
 for(const names of [['idle','walk','idle'],['walk','sprint','walk'],['jump_start','jump','jump_land'],['sitting_enter','sitting_idle','sitting_exit'],['idle','punch_cross','idle'],['spell_simple_enter','spell_simple_shoot','spell_simple_exit']]){
  p=new SpritePlayer(manifest.animations);p.playSequence(names,false);p.advance(names.reduce((sum,n)=>sum+manifest.animations[n].duration,0)+.01);assert.equal(p.name,names.at(-1));assert.equal(p.finished,true);
 }
 assert.equal(manifest.animations.idle.frameCount,15);assert.equal(manifest.animations.idle.duration,2.5);
}
console.log('PASS immediate/queued switches, one-shot hold/repeat, sequences, leftover time, pause, seek and real presets');
// A/B review must preserve paused poses, sequence position and queued switches.
const reviewPath=path.join(__dirname,'../output/universal/review-sprites.json');
if(fs.existsSync(reviewPath)){
 const review=JSON.parse(fs.readFileSync(reviewPath,'utf8'));
 const rc=review.animations;
 const edits=Object.fromEntries(Object.keys(rc).filter(n=>rc[n].variantOf).map(n=>[rc[n].variantOf,n]));
 const base=n=>rc[n].variantOf||n;
 const edited=n=>edits[base(n)]||base(n);
 p=new SpritePlayer(rc,'idle');p.seek(7);const before=p.time;
 p.remapClips(edited);assert.equal(p.name,edits.idle);assert.equal(p.frameIndex,7);assert.equal(p.time,before);assert.equal(p.playing,false);
 p.remapClips(base);assert.equal(p.name,'idle');assert.equal(p.frameIndex,7);
 p.playSequence(['idle','walk','idle'],true);p.advance(rc.idle.duration+.3);
 p.remapClips(edited);assert.equal(p.name,edited('walk'));assert.equal(p.sequenceIndex,1);assert.ok(Math.abs(p.time-.3)<1e-8);
 assert.deepEqual(p.sequence,[edits.idle,edited('walk'),edits.idle]);
 p.advance(rc.walk.duration);assert.equal(p.name,edits.idle);assert.equal(p.sequenceIndex,2);
 p.select('walk');p.select('idle',true);p.remapClips(edited);assert.equal(p.pending,edits.idle);
 p.advance(rc.walk.duration);assert.equal(p.name,edits.idle);
 p.playSequence(['idle'],false);p.advance(5);p.remapClips(edited);
 assert.equal(p.finished,true);assert.equal(p.playing,false);assert.equal(p.frameIndex,rc[edits.idle].frameCount-1);
 if(edits.walk){
  p.select('walk');p.seek(8);p.remapClips(edited);assert.equal(p.name,edits.walk);assert.equal(p.frameIndex,8);assert.equal(p.playing,false);
  p.remapClips(base);assert.equal(p.name,'walk');assert.equal(p.frameIndex,8);
  assert.deepEqual(rc[edits.walk].sourceFrames,rc.walk.sourceFrames);assert.equal(rc[edits.walk].duration,rc.walk.duration);
 }
 const covered=Object.keys(manifest.animations).filter(n=>['Movement','Combat','Magic'].includes(manifest.animations[n].category));
 covered.push(...Object.keys(rc).filter(n=>n.startsWith('ual2_')&&!rc[n].variantOf));
 assert.deepEqual(Object.keys(edits).sort(),covered.sort(),'Every Movement, Combat, Magic and UAL2 clip should have one edited counterpart');
 for(const [original,changed] of Object.entries(edits)){
  assert.deepEqual(rc[changed].sourceFrames,rc[original].sourceFrames,'Sampling changed: '+original);
  for(const key of ['frameCount','fps','duration','loop'])assert.equal(rc[changed][key],rc[original][key],original+' '+key);
  p=new SpritePlayer(rc,original);const frame=Math.floor(rc[original].frameCount/2);p.seek(frame);
  p.remapClips(edited);assert.equal(p.name,changed);assert.equal(p.frameIndex,frame);assert.equal(p.playing,false);
  p.remapClips(base);assert.equal(p.name,original);assert.equal(p.frameIndex,frame);
  if(!rc[original].loop){p.select(changed);p.advance(rc[changed].duration+.1);p.remapClips(base);assert.equal(p.finished,true);assert.equal(p.frameIndex,rc[original].frameCount-1);}
 }
 for(const names of [['sword_idle','sword_attack','sword_idle'],['spell_simple_idle','spell_simple_shoot','spell_simple_idle'],['pistol_idle','pistol_shoot','pistol_idle']]){
  p=new SpritePlayer(rc);const sequence=names.map(edited);p.playSequence(sequence,false);
  p.advance(sequence.reduce((sum,n)=>sum+rc[n].duration,0)+.01);
  assert.equal(p.name,sequence.at(-1));assert.equal(p.finished,true);
 }
 for(const [name,clip] of Object.entries(manifest.animations))assert.deepEqual(rc[name],clip,'Baseline clip changed: '+name);
 assert.deepEqual(review.pivot,manifest.pivot);assert.deepEqual(review.frameSize,manifest.frameSize);
 for(const clip of Object.values(rc))assert.ok(fs.existsSync(path.join(__dirname,'../output/universal',clip.image)));
 if(rc.ual2_slide_start){
  const added=Object.keys(rc).filter(n=>n.startsWith('ual2_')&&!rc[n].variantOf);
  const sourceCatalog=JSON.parse(fs.readFileSync(path.join(__dirname,'../assets/quaternius/universal/animations-library2.json'),'utf8'));
  const expected=sourceCatalog.filter(c=>c.source_action!=='A_TPose');
  assert.equal(added.length,42);
  assert.deepEqual(added.map(n=>rc[n].sourceAction).sort(),expected.map(c=>c.action).sort(),'Every free UAL2 motion is exported');
  for(const name of added){assert.equal(rc[name].variantOf,undefined);assert.equal(rc[edited(name)].variantOf,name);}
  for(const sequence of [
   ['ual2_ninjajump_start','ual2_ninjajump_idle_loop','ual2_ninjajump_land'],
   ['ual2_slide_start','ual2_slide_loop','ual2_slide_exit'],
   ['idle','ual2_sword_regular_combo','idle'],
   ['idle','ual2_melee_hook','ual2_melee_hook_rec'],
   ['idle','ual2_sword_heavy_combo','idle'],
   ['ual2_idle_shield_loop','ual2_shield_dash','ual2_idle_shield_loop'],
   ['ual2_zombie_idle_loop','ual2_zombie_walk_fwd_loop','ual2_zombie_idle_loop'],
   ['ual2_farm_plantseed','ual2_farm_watering','ual2_farm_harvest'],
  ]){
   p=new SpritePlayer(rc);p.playSequence(sequence,false);p.remapClips(edited);
   p.advance(sequence.reduce((sum,n)=>sum+rc[n].duration,0)+.01);
   assert.equal(p.finished,true);assert.equal(p.name,edited(sequence.at(-1)));
  }
  console.log('PASS all 42 UAL2 edits and mixed-library edited sequence presets');
 }
 console.log('PASS base/edited phase, pause, running sequence, queued switch, held pose, baseline preservation and image paths');
}
