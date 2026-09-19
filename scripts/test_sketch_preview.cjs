// Confirm the new mesh uses the same motion samples and comparison controls.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const SpritePlayer=require('./player.js');
const root=path.join(__dirname,'../output/universal');
const baseline=JSON.parse(fs.readFileSync(path.join(root,'review-sprites.json'),'utf8'));
const model=JSON.parse(fs.readFileSync(path.join(root,'sketch-hero/sprites.json'),'utf8'));
assert.equal(model.defaultEdited,true);
const clips=model.animations;
assert.equal(Object.keys(clips).length,20);
for(const [name,clip] of Object.entries(clips)){
 const original=baseline.animations[name];assert.ok(original,name);
 for(const key of ['sourceAction','sourceFrames','frameCount','fps','duration','loop'])assert.deepEqual(clip[key],original[key],name+' '+key);
 assert.ok(fs.existsSync(path.join(root,'sketch-hero',clip.image)));
 if(clip.variantOf){
  const p=new SpritePlayer(clips,clip.variantOf);const frame=Math.floor(clip.frameCount/2);p.seek(frame);
  p.remapClips(n=>n===clip.variantOf?name:n);assert.equal(p.name,name);assert.equal(p.frameIndex,frame);assert.equal(p.playing,false);
 }
}
for(const sequence of [['idle','walk','idle'],['walk','sprint','walk'],['jump_start','jump','jump_land'],['sword_idle','sword_attack','sword_idle'],['spell_simple_idle','spell_simple_shoot','spell_simple_idle']]){
 const p=new SpritePlayer(clips);p.playSequence(sequence,false);p.advance(sequence.reduce((t,n)=>t+clips[n].duration,0)+.01);assert.equal(p.finished,true);
}
console.log('PASS Sketch Hero: all 20 clips match original motion samples; A/B frame continuity and five transition presets');
