/* Deterministic sprite playback; shared by the preview and Node regression tests. */
(function (root) {
  class SpritePlayer {
    constructor(clips, initial) {
      this.clips = clips;
      this.name = initial || Object.keys(clips)[0];
      this.time = 0;
      this.playing = true;
      this.finished = false;
      this.repeatClip = false;
      this.pending = null;
      this.sequence = null;
      this.sequenceIndex = 0;
      this.repeatSequence = false;
      this.transition = null;
    }
    get clip() { return this.clips[this.name]; }
    get frameIndex() { return Math.min(this.clip.frameCount - 1, Math.max(0, Math.floor(this.time * this.clip.fps + 1e-8))); }
    validate(name) { if (!this.clips[name]) throw new Error('Unknown animation: ' + name); }
    enter(name, reason, carry = 0) {
      this.validate(name);
      this.transition = {from: this.name, to: name, reason, fromFrame: this.frameIndex};
      this.name = name;
      this.time = carry;
      this.finished = false;
    }
    select(name, atEnd = false) {
      this.validate(name);
      this.sequence = null;
      if (atEnd && !this.finished) { this.pending = name; this.playing = true; }
      else { this.pending = null; this.enter(name, 'Immediate switch'); this.playing = true; }
    }
    playSequence(names, repeat = false) {
      if (!names.length) throw new Error('Choose at least one animation.');
      names.forEach(name => this.validate(name));
      this.sequence = names.slice();
      this.sequenceIndex = 0;
      this.repeatSequence = repeat;
      this.pending = null;
      this.enter(names[0], 'Sequence start');
      this.playing = true;
    }
    remapClips(resolve) {
      // Change the version of a pose without restarting playback or a sequence.
      const name = resolve(this.name);
      const pending = this.pending ? resolve(this.pending) : null;
      const sequence = this.sequence ? this.sequence.map(resolve) : null;
      [name, pending, ...(sequence || [])].filter(Boolean).forEach(n => this.validate(n));
      if (name !== this.name) {
        const phase = Math.min(1, this.time / this.clip.duration);
        this.transition = {from: this.name, to: name, reason: 'Base / edited comparison', fromFrame: this.frameIndex};
        this.name = name;
        this.time = phase * this.clip.duration;
      }
      this.pending = pending;
      this.sequence = sequence;
    }
    toggle() {
      if (this.finished) { this.select(this.name); return; }
      this.playing = !this.playing;
    }
    seek(frame) {
      this.time = Math.min(this.clip.frameCount - 1, Math.max(0, frame)) / this.clip.fps;
      this.playing = false;
      this.finished = false;
      this.pending = null;
      this.sequence = null;
    }
    advance(seconds) {
      if (!this.playing || !Number.isFinite(seconds) || seconds <= 0) return;
      this.time += seconds;
      while (this.time + 1e-9 >= this.clip.duration) {
        const carry = Math.max(0, this.time - this.clip.duration);
        if (this.pending) {
          const next = this.pending;
          this.pending = null;
          this.enter(next, 'Clip boundary', carry);
        } else if (this.sequence) {
          if (this.sequenceIndex + 1 < this.sequence.length) {
            this.sequenceIndex++;
            this.enter(this.sequence[this.sequenceIndex], 'Sequence boundary', carry);
          } else if (this.repeatSequence) {
            this.sequenceIndex = 0;
            this.enter(this.sequence[0], 'Sequence repeat', carry);
          } else { this.hold(); break; }
        } else if (this.clip.loop || this.repeatClip) {
          this.time %= this.clip.duration;
          break;
        } else { this.hold(); break; }
      }
    }
    hold() { this.time = this.clip.duration; this.finished = true; this.playing = false; }
  }
  if (typeof module !== 'undefined' && module.exports) module.exports = SpritePlayer;
  else root.SpritePlayer = SpritePlayer;
})(typeof globalThis !== 'undefined' ? globalThis : this);
