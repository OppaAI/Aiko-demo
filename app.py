from dotenv import load_dotenv
load_dotenv()

import gradio as gr
from core.wakeup import AikoWakeup

result = AikoWakeup(text_mode=True).boot(
    on_loading=lambda k: print(f"[boot] loading: {k}"),
    on_done   =lambda k: print(f"[boot]    done: {k}"),
    on_skip   =lambda k: print(f"[boot]    skip: {k}"),
)
think    = result.think
memorize = result.memorize

if hasattr(think, "join_warmup"):
    think.join_warmup()


def chat(message, history):
    tokens = []
    def _cb(token):
        if token.startswith("__SEARCHING__:"):
            query = token.split(":", 1)[1].strip()
            tokens.append(f"\n🔍 Searching: *{query}*\n")
        else:
            tokens.append(token)
    think.chat(message, token_callback=_cb)
    return "".join(tokens)


# ── VRM viewer ────────────────────────────────────────────────────────────────
# three-vrm v3 via CDN — no combineSkeletons, no rotateVRM0 (both removed in v3)
# VRM served from /static/Aiko.vrm (Gradio static folder)
# Includes: idle breath/sway, head wander, arms behind back, blink, auto-neutral

_VRM_VIEWER = """
<div id="aiko-vrm-root" style="width:100%;height:520px;position:relative;background:#0a0a0f;border-radius:12px;overflow:hidden;">

  <!-- loading overlay -->
  <div id="vrm-loading" style="position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:12px;font-family:monospace;z-index:10;">
    <div style="font-size:13px;letter-spacing:0.25em;color:#9b7fd4;">AIKO-CHAN</div>
    <div style="width:140px;height:1px;background:#1a1a2f;overflow:hidden;">
      <div id="vrm-load-fill" style="height:100%;width:0%;background:#7b4fd4;box-shadow:0 0 6px #7b4fd4;transition:width 0.3s;"></div>
    </div>
    <div id="vrm-load-msg" style="font-size:10px;color:#3a2a5a;letter-spacing:0.15em;">loading runtime…</div>
  </div>

  <canvas id="aiko-canvas" style="width:100%;height:100%;display:block;"></canvas>

  <!-- status pill -->
  <div style="position:absolute;top:10px;right:12px;font-family:monospace;font-size:10px;color:#3a2a5a;letter-spacing:0.1em;">
    <span id="vrm-status">●</span> aiko
  </div>
  <!-- emotion readout -->
  <div id="vrm-emotion" style="position:absolute;bottom:10px;left:12px;font-family:monospace;font-size:10px;color:#3a2a5a;letter-spacing:0.12em;text-transform:uppercase;">—</div>
</div>

<script type="importmap">
{
  "imports": {
    "three":          "https://cdn.jsdelivr.net/npm/three@0.170.0/build/three.module.js",
    "three/addons/":  "https://cdn.jsdelivr.net/npm/three@0.170.0/examples/jsm/",
    "@pixiv/three-vrm": "https://cdn.jsdelivr.net/npm/@pixiv/three-vrm@3/lib/three-vrm.module.min.js"
  }
}
</script>

<script type="module">
import * as THREE from 'three';
import { OrbitControls }  from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader }     from 'three/addons/loaders/GLTFLoader.js';
import { VRMLoaderPlugin, VRMUtils } from '@pixiv/three-vrm';

const VRM_URL = '/static/Aiko.vrm';

const root    = document.getElementById('aiko-vrm-root');
const canvas  = document.getElementById('aiko-canvas');
const loading = document.getElementById('vrm-loading');
const fill    = document.getElementById('vrm-load-fill');
const msg     = document.getElementById('vrm-load-msg');
const status  = document.getElementById('vrm-status');
const emotionEl = document.getElementById('vrm-emotion');

// ── renderer ──────────────────────────────────────────────────────────────────
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.setClearColor(0x0a0a0f);

const scene  = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(28, 1, 0.1, 100);
camera.position.set(0, 1.35, 2.8);

const controls = new OrbitControls(camera, canvas);
controls.target.set(0, 1.1, 0);
controls.enableDamping  = true;
controls.dampingFactor  = 0.08;
controls.minDistance    = 0.8;
controls.maxDistance    = 6;
controls.update();

// ── lighting ──────────────────────────────────────────────────────────────────
scene.add(new THREE.AmbientLight(0xc8b0ff, 0.55));
const key = new THREE.DirectionalLight(0xffffff, 1.2);
key.position.set(1, 3, 2); scene.add(key);
const rim = new THREE.DirectionalLight(0x7b4fd4, 0.45);
rim.position.set(-2, 1, -1); scene.add(rim);
const fill2 = new THREE.DirectionalLight(0xd4b0ff, 0.25);
fill2.position.set(0, -1, 2); scene.add(fill2);
scene.add(new THREE.GridHelper(10, 20, 0x1a0a2a, 0x100820));

// ── resize ────────────────────────────────────────────────────────────────────
function resize() {
  const w = root.clientWidth, h = root.clientHeight;
  renderer.setSize(w, h, false);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}
resize();
new ResizeObserver(resize).observe(root);

// ── state ─────────────────────────────────────────────────────────────────────
let vrm = null;
const clock = new THREE.Clock();

// Expression lerp
const exprTargets = {}, exprCurrent = {};
const EXPR_LERP = 6;

// Auto-return to neutral when Python goes quiet
let exprResetTimer = null;
const EXPR_RESET_DELAY = 4000;

// Blink state machine
let blinkTimer = 3.0 + Math.random() * 4.0;
let blinkPhase = 'wait'; // 'wait' | 'closing' | 'opening'
let blinkT = 0;
const BLINK_CLOSE = 0.07;
const BLINK_OPEN  = 0.10;

// Idle time accumulator
let t = 0;

// Resting pose — arms behind back (parade rest)
// Upper arms swing back and inward; lower arms cross behind hips
const REST = {
  leftUpperArm:  { x: -1.1, z: -0.6 },
  rightUpperArm: { x: -1.1, z:  0.6 },
  leftLowerArm:  { x: -0.5, z: -0.4 },
  rightLowerArm: { x: -0.5, z:  0.4 },
  leftHand:      { y:  0.4 },
  rightHand:     { y: -0.4 },
};

// ── idle procedural animation ─────────────────────────────────────────────────
// All frequencies are irrational so motions never visibly loop
function applyIdle(dt) {
  if (!vrm || !vrm.humanoid) return;
  t += dt;
  const get = name => vrm.humanoid.getRawBoneNode(name);

  // Breathing — chest + belly
  const breath = Math.sin(t * 0.83) * 0.013;
  const chest  = get('chest');
  const spine  = get('spine');
  if (chest) chest.rotation.x = breath;
  if (spine) spine.rotation.x = breath * 0.5;

  // Hip sway — slow side-to-side + subtle forward rock
  const hips = get('hips');
  if (hips) {
    hips.rotation.z  = Math.sin(t * 0.41) * 0.012;
    hips.rotation.x  = Math.sin(t * 0.67) * 0.008;
    hips.position.x  = Math.sin(t * 0.41) * 0.003;
  }

  // Head — slow wander with multiple overlapping waves
  const head = get('head');
  if (head) {
    head.rotation.y = Math.sin(t * 0.31) * 0.055 + Math.sin(t * 1.13) * 0.012;
    head.rotation.z = Math.sin(t * 0.27 + 1.1) * 0.018 + Math.sin(t * 0.71) * 0.006;
    head.rotation.x = Math.sin(t * 0.53) * 0.012;
  }

  // Neck follows head at reduced scale
  const neck = get('neck');
  if (neck && head) {
    neck.rotation.y = head.rotation.y * 0.3;
    neck.rotation.z = head.rotation.z * 0.3;
  }

  // Arms — rest offset + per-bone subtle drift
  const lUA = get('leftUpperArm'),  rUA = get('rightUpperArm');
  const lLA = get('leftLowerArm'),  rLA = get('rightLowerArm');
  const lH  = get('leftHand'),      rH  = get('rightHand');

  if (lUA) { lUA.rotation.x = REST.leftUpperArm.x  + Math.sin(t * 0.47) * 0.012;
             lUA.rotation.z = REST.leftUpperArm.z  + Math.sin(t * 0.41) * 0.008; }
  if (rUA) { rUA.rotation.x = REST.rightUpperArm.x + Math.sin(t * 0.53 + 0.9) * 0.012;
             rUA.rotation.z = REST.rightUpperArm.z + Math.sin(t * 0.37 + 0.7) * 0.008; }
  if (lLA) { lLA.rotation.x = REST.leftLowerArm.x  + Math.sin(t * 0.61) * 0.010;
             lLA.rotation.z = REST.leftLowerArm.z  + Math.sin(t * 0.43) * 0.006; }
  if (rLA) { rLA.rotation.x = REST.rightLowerArm.x + Math.sin(t * 0.57 + 1.4) * 0.010;
             rLA.rotation.z = REST.rightLowerArm.z + Math.sin(t * 0.51 + 0.5) * 0.006; }
  if (lH)    lH.rotation.y  = REST.leftHand.y  + Math.sin(t * 0.33) * 0.008;
  if (rH)    rH.rotation.y  = REST.rightHand.y + Math.sin(t * 0.29 + 1.2) * 0.008;
}

// ── blink ─────────────────────────────────────────────────────────────────────
function applyBlink(dt) {
  if (!vrm || !vrm.expressionManager) return;
  const em = vrm.expressionManager;

  if (blinkPhase === 'wait') {
    blinkTimer -= dt;
    if (blinkTimer <= 0) { blinkPhase = 'closing'; blinkT = 0; }

  } else if (blinkPhase === 'closing') {
    blinkT += dt;
    const w = Math.min(blinkT / BLINK_CLOSE, 1.0);
    try { em.setValue('blink', w); } catch(_) {}
    if (blinkT >= BLINK_CLOSE) { blinkPhase = 'opening'; blinkT = 0; }

  } else if (blinkPhase === 'opening') {
    blinkT += dt;
    const w = 1.0 - Math.min(blinkT / BLINK_OPEN, 1.0);
    try { em.setValue('blink', w); } catch(_) {}
    if (blinkT >= BLINK_OPEN) {
      blinkPhase = 'wait';
      blinkTimer = 3.0 + Math.random() * 4.0;
      try { em.setValue('blink', 0); } catch(_) {}
    }
  }
}

// ── render loop ───────────────────────────────────────────────────────────────
function animate() {
  requestAnimationFrame(animate);
  const dt = Math.min(clock.getDelta(), 0.05); // cap dt on tab-switch
  controls.update();

  if (vrm) {
    vrm.update(dt);

    // lerp expression targets (blink driven separately — don't clobber it)
    const em = vrm.expressionManager;
    if (em) {
      for (const [name, target] of Object.entries(exprTargets)) {
        const cur  = exprCurrent[name] ?? 0;
        const next = cur + (target - cur) * Math.min(1, EXPR_LERP * dt);
        exprCurrent[name] = next;
        if (name !== 'blink') try { em.setValue(name, next); } catch(_) {}
      }
    }

    applyBlink(dt);
    applyIdle(dt);
  }

  renderer.render(scene, camera);
}
animate();

// ── load vrm ──────────────────────────────────────────────────────────────────
function setProgress(p, text) {
  fill.style.width = (p * 100) + '%';
  if (text) msg.textContent = text;
}

const loader = new GLTFLoader();
loader.register(parser => new VRMLoaderPlugin(parser));

setProgress(0.05, 'fetching model…');

loader.load(
  VRM_URL,
  (gltf) => {
    setProgress(0.92, 'building…');
    vrm = gltf.userData.vrm;

    // v3: removeUnnecessaryVertices is the only VRMUtils call needed;
    // combineSkeletons and rotateVRM0 were removed — v3 handles both internally
    VRMUtils.removeUnnecessaryVertices(vrm.scene);

    vrm.scene.traverse(o => { if (o.frustumCulled) o.frustumCulled = false; });
    scene.add(vrm.scene);

    if (vrm.expressionManager) {
      vrm.expressionManager.expressions.forEach(ex => {
        exprTargets[ex.expressionName]  = 0;
        exprCurrent[ex.expressionName] = 0;
      });
    }

    setProgress(1.0, 'ready');
    status.style.color = '#7b4fd4';
    setTimeout(() => {
      loading.style.transition = 'opacity 0.8s';
      loading.style.opacity    = '0';
      setTimeout(() => loading.style.display = 'none', 800);
    }, 400);
  },
  (prog) => {
    const p = prog.total ? prog.loaded / prog.total : 0;
    setProgress(0.05 + p * 0.85, 'loading model…');
  },
  (err) => {
    msg.textContent = 'failed to load vrm';
    status.style.color = '#d45050';
    console.error('[aiko-vrm]', err);
  }
);

// ── expression API — callable from Python via Gradio JS or page JS ────────────
// window.aikoSetExpression('happy', 0.9)
// window.aikoSetViseme('A', 0.8)
window.aikoSetExpression = (name, intensity = 1.0) => {
  for (const k of Object.keys(exprTargets)) {
    if (k !== 'blink') exprTargets[k] = 0; // preserve blink state
  }
  if (name && name !== 'neutral') exprTargets[name] = intensity;

  // update emotion readout
  emotionEl.textContent = (name && name !== 'neutral')
    ? name + ' · ' + Math.round(intensity * 100) + '%'
    : '—';
  emotionEl.style.color = (name && name !== 'neutral') ? '#9b7fd4' : '#3a2a5a';

  // auto-return to neutral after delay if Python goes quiet
  clearTimeout(exprResetTimer);
  if (name && name !== 'neutral') {
    exprResetTimer = setTimeout(() => window.aikoSetExpression('neutral'), 4000);
  }
};

window.aikoSetViseme = (viseme, weight = 1.0) => {
  const map = { A:'aa', I:'ih', U:'ou', E:'ee', O:'oh' };
  const v   = map[viseme] ?? viseme;
  ['aa','ih','ou','ee','oh'].forEach(k => exprTargets[k] = 0);
  exprTargets[v] = weight;
};
</script>
"""

# ── speech js (tts + asr) ─────────────────────────────────────────────────────
_SPEECH_JS = """
<script>
(function () {
    const TTS_RATE = 1.05, TTS_PITCH = 1.1, TTS_LANG = 'en-US', ASR_LANG = 'en-US';
    let ttsEnabled = true, lastSpoken = '', recognition = null, isListening = false;

    function waitFor(selector, cb, interval=200, maxTries=50) {
        let tries=0;
        const id = setInterval(()=>{
            const el=document.querySelector(selector);
            if(el){clearInterval(id);cb(el);}
            if(++tries>=maxTries) clearInterval(id);
        }, interval);
    }
    function stripMarkdown(text) {
        return text
            .replace(/🔍 Searching:.*/g,'')
            .replace(/\*\*(.*?)\*\*/g,'$1')
            .replace(/\*(.*?)\*/g,'$1')
            .replace(/`{1,3}[^`]*`{1,3}/g,'')
            .replace(/#{1,6}\s/g,'')
            .replace(/\n+/g,' ').trim();
    }
    function speak(text) {
        if(!ttsEnabled||!text) return;
        const clean=stripMarkdown(text);
        if(!clean||clean===lastSpoken) return;
        lastSpoken=clean;
        window.speechSynthesis.cancel();
        const utt=new SpeechSynthesisUtterance(clean);
        utt.lang=TTS_LANG; utt.rate=TTS_RATE; utt.pitch=TTS_PITCH;
        const voices=window.speechSynthesis.getVoices();
        const female=voices.find(v=>v.lang.startsWith('en')&&/female|woman|girl/i.test(v.name))
                    ||voices.find(v=>v.lang.startsWith('en'));
        if(female) utt.voice=female;
        window.speechSynthesis.speak(utt);
    }
    function watchChatbot(chatbot) {
        const observer=new MutationObserver(()=>{
            const bubbles=chatbot.querySelectorAll('.message.bot,[data-testid="bot"] .md');
            if(!bubbles.length) return;
            const last=bubbles[bubbles.length-1];
            speak(last.innerText||last.textContent||'');
        });
        observer.observe(chatbot,{childList:true,subtree:true});
    }
    function buildMicButton() {
        const btn=document.createElement('button');
        btn.id='aiko-mic-btn'; btn.innerHTML='🎤'; btn.title='Click to speak';
        Object.assign(btn.style,{position:'fixed',bottom:'22px',right:'60px',zIndex:'9999',
            background:'rgba(30,30,30,0.85)',border:'1.5px solid #888',borderRadius:'50%',
            width:'38px',height:'38px',fontSize:'18px',cursor:'pointer',
            display:'flex',alignItems:'center',justifyContent:'center',
            boxShadow:'0 2px 8px rgba(0,0,0,0.4)'});
        document.body.appendChild(btn);
        const SpeechRec=window.SpeechRecognition||window.webkitSpeechRecognition;
        if(!SpeechRec){btn.style.opacity='0.4';btn.style.cursor='not-allowed';return;}
        recognition=new SpeechRec();
        recognition.lang=ASR_LANG; recognition.interimResults=false; recognition.maxAlternatives=1;
        recognition.onresult=(e)=>{
            const transcript=e.results[0][0].transcript.trim();
            if(!transcript) return;
            const inputEl=document.querySelector('.gradio-container textarea')||document.querySelector('textarea');
            if(!inputEl) return;
            const proto=Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype,'value');
            proto.set.call(inputEl,transcript);
            inputEl.dispatchEvent(new Event('input',{bubbles:true}));
            setTimeout(()=>{
                const submitBtn=document.querySelector('button.submit')
                    ||document.querySelector('#component-submit-btn')
                    ||document.querySelector('[data-testid="submit-btn"]')
                    ||[...document.querySelectorAll('button')].find(
                        b=>b.getAttribute('aria-label')==='Submit'||
                           b.textContent.trim()==='↵'||
                           b.textContent.trim()==='Submit');
                if(submitBtn) submitBtn.click();
            },200);
        };
        recognition.onstart=()=>{isListening=true;btn.innerHTML='🔴';btn.style.background='rgba(255,50,50,0.25)';window.speechSynthesis.cancel();};
        recognition.onend=()=>{isListening=false;btn.innerHTML='🎤';btn.style.background='rgba(30,30,30,0.85)';};
        recognition.onerror=(e)=>{console.warn('[aiko-asr]',e.error);isListening=false;btn.innerHTML='🎤';btn.style.background='rgba(30,30,30,0.85)';};
        btn.addEventListener('click',()=>{if(isListening){recognition.stop();}else{try{recognition.start();}catch(e){console.warn(e);}}});
    }
    function buildTTSToggle() {
        const btn=document.createElement('button');
        btn.innerHTML='🔊'; btn.title='Toggle voice';
        Object.assign(btn.style,{position:'fixed',bottom:'22px',right:'12px',zIndex:'9999',
            background:'rgba(30,30,30,0.85)',border:'1.5px solid #888',borderRadius:'50%',
            width:'38px',height:'38px',fontSize:'18px',cursor:'pointer',
            boxShadow:'0 2px 8px rgba(0,0,0,0.4)'});
        btn.addEventListener('click',()=>{ttsEnabled=!ttsEnabled;btn.innerHTML=ttsEnabled?'🔊':'🔇';if(!ttsEnabled)window.speechSynthesis.cancel();});
        document.body.appendChild(btn);
    }
    window.addEventListener('load',()=>{
        if(window.speechSynthesis.onvoiceschanged!==undefined) window.speechSynthesis.onvoiceschanged=()=>{};
        buildTTSToggle();
        buildMicButton();
        waitFor('.chatbot,[data-testid="chatbot"]',watchChatbot);
    });
})();
</script>
"""

# ── gradio ui ─────────────────────────────────────────────────────────────────
with gr.Blocks(
    title="Aiko-chan 🌸",
    css="""
    #aiko-col { padding: 0 !important; }
    #aiko-chatbot { height: 480px; }
    .gradio-container { max-width: 1200px !important; }
    """
) as demo:
    gr.HTML(_SPEECH_JS)

    with gr.Row():
        # ── left: chat ────────────────────────────────────────────────────────
        with gr.Column(scale=6):
            gr.ChatInterface(
                fn=chat,
                title="Aiko-chan 🌸",
                chatbot=gr.Chatbot(elem_id="aiko-chatbot"),
            )

        # ── right: vrm viewer ─────────────────────────────────────────────────
        with gr.Column(scale=4, elem_id="aiko-col"):
            gr.HTML(_VRM_VIEWER)

demo.launch(
    server_name="0.0.0.0",
    server_port=7860,
    ssr_mode=False,
)