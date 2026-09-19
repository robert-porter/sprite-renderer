// Exercise the actual preview loader without decoding a multi-gigabyte catalog.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const SpritePlayer = require('./player.js');
const html = fs.readFileSync(__dirname + '/preview.html', 'utf8');
const loader = html.slice(html.indexOf('function loading()'), html.indexOf('function library()'));
const clips = Object.fromEntries(Array.from({length:20}, (_, i) => ['clip'+i, {
  image:'clip'+i+'.png', duration:1, fps:4, frameCount:4, loop:true,
}]));
clips.edited = {...clips.clip0, image:'edited.png', variantOf:'clip0'};
const images = new Map();
const player = new SpritePlayer(clips, 'clip0');
const status = {};
class FakeImage {
  set src(value) {this.path=value; this.complete=false; this.naturalWidth=0;}
  get src() {return this.path;}
  finish() {this.complete=true; this.naturalWidth=4096; this.onload?.();}
}
const context = vm.createContext({images, player, clips, allNames:Object.keys(clips),
  edits:{clip0:'edited'}, baseName:name=>clips[name].variantOf||name,
  sheetUrl:name=>clips[name].image+'?v=test', Image:FakeImage, $:()=>status});
vm.runInContext(loader, context);
const prepare = () => vm.runInContext('prepareImages()', context);
prepare();
assert.deepEqual([...images.keys()], ['clip0','edited']);
const original = images.get('clip0');
original.finish();
assert.match(status.textContent, /1 cached/);
player.select('clip1', true); prepare();
assert.ok(images.has('clip1'), 'Queued animation is prefetched before the cut');
player.playSequence(['clip2','clip3','clip4'], true); prepare();
for(const name of ['clip2','clip3','clip4'])assert.ok(images.has(name));
for(let i=5;i<20;i++){player.select('clip'+i);prepare();assert.ok(images.size<=8);}
assert.equal(original.src,'', 'Eviction releases the image source');
assert.equal(images.has('clip0'),false);
player.select('clip0');prepare();
assert.notEqual(images.get('clip0'),original, 'An evicted sheet can be loaded again');
assert.ok(images.has('edited'), 'A/B counterpart stays ready');
images.get('clip0').onerror();
assert.match(status.textContent,/1 failed/);
console.log('PASS bounded sprite cache, queued/sequence prefetch, A/B pair, eviction, revisit and load failures');
