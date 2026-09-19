/* Independent sprite layers, composed per pixel with shared camera depth. */
(function(root) {
  class SwordDepthPreview {
    constructor(spec, host, selectClip) {
      this.spec = spec;
      this.cache = new Map();
      this.lastKey = null;
      this.canvas = document.createElement('canvas');
      this.canvas.width = spec.frameSize[0];
      this.canvas.height = spec.frameSize[1];
      const panel = document.createElement('div');
      panel.className = 'sword-picker pad';
      panel.style.borderBottom = '1px solid var(--edge)';
      panel.innerHTML = '<label for="sword-picker">Test sword</label><div class="row"><select id="sword-picker"><option value="none">None</option></select><button id="try-swords">Try Sword Idle</button></div><label for="sword-view">Sword preview view</label><select id="sword-view"><option value="0">Composed</option><option value="1">Character depth</option><option value="2">Sword depth</option><option value="3">Sword only</option></select><p id="sword-status" class="small" aria-live="polite"></p>';
      host.prepend(panel);
      this.picker = panel.querySelector('#sword-picker');
      this.view = panel.querySelector('#sword-view');
      this.status = panel.querySelector('#sword-status');
      const trailLabel=document.createElement('label');trailLabel.htmlFor='sword-trail';trailLabel.textContent='Sword slash effect';
      this.trail=document.createElement('select');this.trail.id='sword-trail';
      this.trail.innerHTML='<option value="on">Cartoon slash · trial</option><option value="off">Off</option>';
      this.trail.value=new URLSearchParams(location.search).get('trail')==='off'?'off':'on';
      panel.insertBefore(trailLabel,this.status);panel.insertBefore(this.trail,this.status);
      this.picker.parentElement.style.flexWrap = 'wrap';
      this.picker.style.flexBasis = '100%';
      const supportedLabel=document.createElement('label');supportedLabel.htmlFor='sword-animation';supportedLabel.textContent='Sword animation';
      this.animation=document.createElement('select');this.animation.id='sword-animation';
      const baseClips=[...new Set(Object.entries(spec.animations).map(([name,clip])=>clip.baseClip||name.replace(/_edited$/,'')))];
      for(const name of baseClips){const option=document.createElement('option');option.value=name;option.textContent=spec.animations[name]?.label||name.replaceAll('_',' ');this.animation.append(option);}
      panel.insertBefore(supportedLabel,this.picker.parentElement);panel.insertBefore(this.animation,this.picker.parentElement);
      // Keep each label directly above its field.
      panel.insertBefore(panel.querySelector('label[for="sword-picker"]'),this.picker.parentElement);
      this.animation.onchange=()=>{if(this.picker.value==='none')this.picker.value=spec.weapons[0].id;selectClip(this.animation.value);};
      for (const weapon of spec.weapons) {
        const option = document.createElement('option');
        option.value = weapon.id; option.textContent = weapon.label;
        this.picker.append(option);
      }
      const requested = new URLSearchParams(location.search).get('sword');
      if (spec.weapons.some(w => w.id === requested)) this.picker.value = requested;
      panel.querySelector('#try-swords').onclick = () => {
        if (this.picker.value === 'none') this.picker.value = spec.weapons[0].id;
        selectClip(this.animation.value);
      };
      panel.querySelector('#try-swords').textContent='Play sword animation';
      try { this.initGL(); }
      catch (error) { this.error = error.message; }
    }
    initGL() {
      const gl = this.canvas.getContext('webgl', {alpha:true, premultipliedAlpha:false, antialias:false, preserveDrawingBuffer:true});
      if (!gl) throw new Error('WebGL is unavailable. Character preview remains available.');
      this.gl = gl;
      const program = gl.createProgram();
      const sources = [
        [gl.VERTEX_SHADER, 'attribute vec2 p; varying vec2 uv; void main(){gl_Position=vec4(p,0.,1.);uv=vec2((p.x+1.)*.5,(1.-p.y)*.5);}'],
        [gl.FRAGMENT_SHADER, `precision highp float;
          varying vec2 uv; uniform sampler2D bodyColor, bodyDepth, swordColor, swordDepth;
          uniform sampler2D trailColor, trailDepth;
          uniform vec4 rect; uniform int mode, trailEnabled;
          float depth(vec4 d){return (floor(d.r*255.+.5)*256.+floor(d.g*255.+.5))/65534.;}
          vec3 linearize(vec3 c){return mix(c/12.92,pow((c+.055)/1.055,vec3(2.4)),step(vec3(.04045),c));}
          vec3 encode(vec3 c){return mix(c*12.92,1.055*pow(max(c,vec3(0.)),vec3(1./2.4))-.055,step(vec3(.0031308),c));}
          void order(inout vec4 a,inout float az,inout vec4 b,inout float bz){
            if(az>bz){vec4 t=a;a=b;b=t;float tz=az;az=bz;bz=tz;}
          }
          void main(){
            vec2 at=rect.xy+uv*rect.zw;
            vec4 b=texture2D(bodyColor,at),s=texture2D(swordColor,at);
            float bz=depth(texture2D(bodyDepth,at)),sz=depth(texture2D(swordDepth,at));
            if(mode==1){gl_FragColor=vec4(vec3(clamp(1.-bz,0.,1.)),b.a);return;}
            if(mode==2){gl_FragColor=vec4(vec3(clamp(1.-sz,0.,1.)),s.a);return;}
            if(mode==3){gl_FragColor=s;return;}
            vec4 t=vec4(0.);float tz=2.;
            if(trailEnabled==1){t=texture2D(trailColor,at);tz=depth(texture2D(trailDepth,at));}
            order(b,bz,s,sz);order(s,sz,t,tz);order(b,bz,s,sz);
            float alpha=b.a+s.a*(1.-b.a)+t.a*(1.-s.a)*(1.-b.a);
            vec3 rgb=linearize(b.rgb)*b.a+linearize(s.rgb)*s.a*(1.-b.a)+linearize(t.rgb)*t.a*(1.-s.a)*(1.-b.a);
            gl_FragColor=vec4(encode(rgb/max(alpha,.000001)),alpha);
          }`]
      ];
      for (const [type,source] of sources) {
        const shader=gl.createShader(type);gl.shaderSource(shader,source);gl.compileShader(shader);
        if(!gl.getShaderParameter(shader,gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(shader));
        gl.attachShader(program,shader);gl.deleteShader(shader);
      }
      gl.linkProgram(program);
      if(!gl.getProgramParameter(program,gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(program));
      gl.useProgram(program);
      const buffer=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buffer);
      gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,1,-1,-1,1,-1,1,1,-1,1,1]),gl.STATIC_DRAW);
      const position=gl.getAttribLocation(program,'p');gl.enableVertexAttribArray(position);gl.vertexAttribPointer(position,2,gl.FLOAT,false,0,0);
      this.rect=gl.getUniformLocation(program,'rect');this.mode=gl.getUniformLocation(program,'mode');
      this.trailEnabled=gl.getUniformLocation(program,'trailEnabled');
      ['bodyColor','bodyDepth','swordColor','swordDepth','trailColor','trailDepth'].forEach((name,i)=>gl.uniform1i(gl.getUniformLocation(program,name),i));
      gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL,false);
      gl.pixelStorei(gl.UNPACK_COLORSPACE_CONVERSION_WEBGL,gl.NONE);
      this.canvas.addEventListener('webglcontextlost', event => {event.preventDefault();this.error='Depth renderer interrupted; reload the preview to restore it.';});
    }
    texture(url, wanted) {
      if(this.cache.has(url)) {
        const item=this.cache.get(url);this.cache.delete(url);this.cache.set(url,item);return item;
      }
      const gl=this.gl;
      while(this.cache.size>=12) {
        const oldest=[...this.cache.keys()].find(key=>!wanted.includes(key));
        if(!oldest) break;
        const item=this.cache.get(oldest);item.image.onload=item.image.onerror=null;
        item.image.src='';if(item.texture)gl.deleteTexture(item.texture);this.cache.delete(oldest);
      }
      const item={image:new Image(),ready:false};this.cache.set(url,item);
      item.image.onload=()=>{
        try {
          if(item.image.naturalWidth>gl.getParameter(gl.MAX_TEXTURE_SIZE)||item.image.naturalHeight>gl.getParameter(gl.MAX_TEXTURE_SIZE))throw new Error('Depth atlas exceeds this device’s texture limit.');
          item.texture=gl.createTexture();gl.bindTexture(gl.TEXTURE_2D,item.texture);
          gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.NEAREST);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.NEAREST);
          gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);
          gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,gl.RGBA,gl.UNSIGNED_BYTE,item.image);
          if(gl.getError()!==gl.NO_ERROR)throw new Error('Could not upload the depth atlas.');
          item.ready=true;
        }catch(error){item.error=error.message;}
      };
      item.image.onerror=()=>item.error='Could not load '+url;
      item.image.src=url;return item;
    }
    urls(name,index) {
      const clip=this.spec.animations[name],weapon=this.picker.value;
      if(!clip||weapon==='none')return [];
      const page=clip.frames[index].page||0;
      const body=clip.layers.character.pages?.[page]||clip.layers.character;
      const sword=clip.layers[weapon].pages?.[page]||clip.layers[weapon];
      const trail=this.trail?.value==='on'&&clip.layers[weapon].trail?.pages[page];
      return [body.color,body.depth,sword.color,sword.depth,...(trail?[trail.color,trail.depth]:[])];
    }
    readyAt(name,index) {
      if(this.error)return true;
      const urls=this.urls(name,index);
      this.pendingUrls=urls;
      const wanted=[...urls,...(this.displayUrls||[])];
      // Freeze at a page/clip boundary until its matching weapon layers arrive.
      // A failed asset is reported by frame(); it must not lock normal playback.
      return urls.map(url=>this.texture(url,wanted)).every(item=>item.ready||item.error);
    }
    frame(name, index) {
      const weapon=this.picker.value, clip=this.spec.animations[name];
      if(clip)this.animation.value=clip.baseClip||name.replace(/_edited$/,'');
      this.view.disabled=weapon==='none'||!clip;
      if(weapon==='none'){this.status.textContent='No sword equipped · choose a sword and a sword animation.';return null;}
      if(!clip){this.status.textContent='Sword hidden on this animation · choose a sword animation above.';return null;}
      if(this.error){this.status.textContent=this.error;return null;}
      const rect=clip.frames[index],page=rect.page||0;
      const body=clip.layers.character.pages?.[page]||clip.layers.character,sword=clip.layers[weapon].pages?.[page]||clip.layers[weapon];
      const urls=this.urls(name,index);
      const hasTrail=urls.length===6;
      this.displayUrls=urls;
      const items=urls.map(url=>this.texture(url,[...urls,...(this.pendingUrls||[])]));
      const failure=items.find(item=>item.error);
      if(failure){this.status.textContent=failure.error+' · Open through preview.ps1 if using a local file.';return null;}
      if(items.some(item=>!item.ready)){this.status.textContent='Loading sword and depth layers…';return null;}
      this.status.textContent=Number(this.view.value)===1||Number(this.view.value)===2?'Camera depth · brighter pixels are nearer.':hasTrail?'Cartoon slash trial · depth-aware 2D sprites':this.trail?.value==='on'?'Slash trial available on Sword Attack and full regular/heavy combos.':'Independent character + sword · per-pixel depth';
      const key=[name,index,weapon,this.view.value,hasTrail].join('/');
      if(key!==this.lastKey) {
        const gl=this.gl,sheetSize=clip.pages?.[page].sheetSize||clip.sheetSize;
        items.forEach((item,i)=>{gl.activeTexture(gl.TEXTURE0+i);gl.bindTexture(gl.TEXTURE_2D,item.texture);});
        // All sampler units must remain complete even when the effect is disabled.
        if(!hasTrail)for(let i=4;i<6;i++){gl.activeTexture(gl.TEXTURE0+i);gl.bindTexture(gl.TEXTURE_2D,items[i-4].texture);}
        gl.uniform1i(this.trailEnabled,hasTrail?1:0);
        gl.uniform4f(this.rect,rect.x/sheetSize[0],rect.y/sheetSize[1],rect.w/sheetSize[0],rect.h/sheetSize[1]);
        gl.uniform1i(this.mode,Number(this.view.value));gl.viewport(0,0,this.canvas.width,this.canvas.height);
        gl.drawArrays(gl.TRIANGLES,0,6);this.lastKey=key;
      }
      return this.canvas;
    }
  }
  root.SwordDepthPreview=SwordDepthPreview;
})(globalThis);
