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
            tokens.append(f"\n\U0001f50d Searching: *{query}*\n")
        else:
            tokens.append(token)
    think.chat(message, token_callback=_cb)
    return "".join(tokens)


# ── dark lavender glassmorphic CSS ────────────────────────────────────────────
_CSS = """
html, body {
    background: #080612 !important;
    color-scheme: dark !important;
}
body, .gradio-container {
    background: #080612 !important;
    color: #d4c8f0 !important;
}
.gradio-container {
    max-width: 1200px !important;
    background:
        radial-gradient(ellipse 80% 60% at 15% 20%, rgba(91,47,168,0.18) 0%, transparent 60%),
        radial-gradient(ellipse 60% 50% at 85% 80%, rgba(155,127,212,0.10) 0%, transparent 55%),
        #080612 !important;
    min-height: 100vh;
}

/* Force dark on Gradio's theme root vars */
:root, .dark {
    --body-background-fill: #080612 !important;
    --background-fill-primary: #0d0920 !important;
    --background-fill-secondary: #110d24 !important;
    --color-accent: #9b7fd4 !important;
    --neutral-950: #d4c8f0 !important;
    --neutral-900: #c4b8e0 !important;
    --neutral-800: #b4a8d0 !important;
    --neutral-100: #1a1030 !important;
    --neutral-50: #0d0920 !important;
    --input-background-fill: rgba(15,10,30,0.85) !important;
    --input-border-color: rgba(155,127,212,0.3) !important;
    --chatbot-background: rgba(10,7,20,0.8) !important;
    --border-color-primary: rgba(155,127,212,0.2) !important;
    --color-text-body: #d4c8f0 !important;
    --body-text-color: #d4c8f0 !important;
    --block-label-text-color: rgba(196,168,255,0.8) !important;
}

/* Nuke any white panels Gradio injects */
.app, .wrap, footer,
.svelte-1ipelgc, .svelte-byatnx,
[class*="gradio-"] > div,
.block, .form, .gap, .panel {
    background: transparent !important;
    border-color: transparent !important;
}

/* Chat panel */
.gradio-container h1 {
    color: #c4a8ff !important;
    font-family: 'Georgia', serif !important;
    letter-spacing: 0.06em !important;
}

#aiko-chatbot,
.chatbot,
[data-testid="chatbot"] {
    background: rgba(15,10,30,0.65) !important;
    border: 1px solid rgba(155,127,212,0.2) !important;
    border-radius: 16px !important;
    height: 480px !important;
}

/* Message bubbles */
.message.user, [data-testid="user"],
.bubble-wrap.user .bubble {
    background: rgba(91,47,168,0.35) !important;
    border: 1px solid rgba(155,127,212,0.25) !important;
    border-radius: 14px 14px 4px 14px !important;
    color: #e8deff !important;
}
.message.bot, [data-testid="bot"],
.bubble-wrap.bot .bubble {
    background: rgba(20,12,42,0.6) !important;
    border: 1px solid rgba(155,127,212,0.15) !important;
    border-radius: 14px 14px 14px 4px !important;
    color: #d4c8f0 !important;
}

/* Ensure all text inside chatbot is bright enough */
.chatbot *, [data-testid="chatbot"] * {
    color: inherit !important;
}
.message.user *, .bubble-wrap.user * { color: #e8deff !important; }
.message.bot *, .bubble-wrap.bot * { color: #d4c8f0 !important; }

/* Input box */
.gradio-container textarea,
.gradio-container input[type="text"],
textarea, input[type="text"] {
    background: rgba(15,10,30,0.85) !important;
    border: 1px solid rgba(155,127,212,0.25) !important;
    border-radius: 12px !important;
    color: #e8deff !important;
    caret-color: #9b7fd4 !important;
}
textarea:focus, input[type="text"]:focus {
    border-color: rgba(155,127,212,0.5) !important;
    outline: none !important;
    box-shadow: 0 0 0 3px rgba(123,79,212,0.15) !important;
}
textarea::placeholder { color: rgba(155,127,212,0.4) !important; }

/* Submit button */
button[aria-label="Submit"],
button.submit,
#component-submit-btn,
button[type="submit"] {
    background: linear-gradient(135deg, rgba(91,47,168,0.8), rgba(123,79,212,0.7)) !important;
    border: 1px solid rgba(155,127,212,0.4) !important;
    border-radius: 10px !important;
    color: #f0e8ff !important;
}
button[aria-label="Submit"]:hover { background: linear-gradient(135deg, rgba(123,79,212,0.9), rgba(155,127,212,0.8)) !important; }

/* All other buttons and labels */
.gradio-container button { color: #c4a8ff !important; }
.gradio-container button:hover { color: #e8deff !important; }
.gradio-container label,
.gradio-container .label-wrap span,
.gradio-container p,
label, p { color: rgba(196,168,255,0.8) !important; }

/* Scrollbars */
* { scrollbar-width: thin; scrollbar-color: rgba(123,79,212,0.4) rgba(15,10,30,0.3); }
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: rgba(15,10,30,0.3); border-radius: 3px; }
::-webkit-scrollbar-thumb { background: rgba(123,79,212,0.4); border-radius: 3px; }

#aiko-col { padding: 0 !important; }
.gradio-container .row { gap: 16px !important; }
"""

# ── VRM viewer ────────────────────────────────────────────────────────────────
# Scripts loaded sequentially: THREE must be global before OrbitControls/GLTFLoader/three-vrm attach
# unpkg used as CDN (better HF Spaces CSP compat)
_VRM_VIEWER = """
<div id="aiko-vrm-root" style="width:100%;height:520px;position:relative;
     background:rgba(10,8,20,0.7);border-radius:16px;overflow:hidden;
     border:1px solid rgba(155,127,212,0.18);">

  <canvas id="aiko-canvas" style="width:100%;height:100%;display:block;"></canvas>
  <div id="aiko-vrm-status" style="position:absolute;bottom:8px;left:50%;
       transform:translateX(-50%);font-family:monospace;font-size:9px;
       color:rgba(155,127,212,0.5);letter-spacing:2px;white-space:nowrap;">initializing…</div>

<script type="module">
import * as THREE from 'https://unpkg.com/three@0.168.0/build/three.module.js';
import { GLTFLoader } from 'https://unpkg.com/three@0.168.0/examples/jsm/loaders/GLTFLoader.js';
import { VRMLoaderPlugin, VRMUtils } from 'https://unpkg.com/@pixiv/three-vrm@3/lib/three-vrm.module.js';
import { OrbitControls } from 'https://unpkg.com/three@0.168.0/examples/jsm/controls/OrbitControls.js';

const status = document.getElementById('aiko-vrm-status');
const log = msg => { status.textContent = msg; console.log('[aiko-vrm]', msg); };

// ── try fetching VRM from multiple candidate paths ────────────────────────────
const CANDIDATES = [
  '/file=static/Aiko.vrm',
  '/file=static/aiko.vrm',
  './static/Aiko.vrm',
  'static/Aiko.vrm',
  '/static/Aiko.vrm',
];

async function findVRM() {
  for (const path of CANDIDATES) {
    try {
      log(`trying: ${path}`);
      const r = await fetch(path, { method: 'HEAD' });
      if (r.ok) { log(`found: ${path}`); return path; }
      log(`${r.status} at ${path}`);
    } catch(e) {
      log(`err: ${path} — ${e.message}`);
    }
  }
  return null;
}

// ── renderer ──────────────────────────────────────────────────────────────────
const canvas = document.getElementById('aiko-canvas');
const W = canvas.parentElement.clientWidth || 400;
const H = canvas.parentElement.clientHeight || 520;

const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
renderer.setSize(W, H);
renderer.setPixelRatio(window.devicePixelRatio);
renderer.outputColorSpace = THREE.SRGBColorSpace;

const scene  = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(30, W / H, 0.1, 20);
camera.position.set(0, 1.4, 3.5);

const controls = new OrbitControls(camera, renderer.domElement);
controls.target.set(0, 1.0, 0);
controls.enableDamping = true;
controls.dampingFactor = 0.08;
controls.update();

scene.add(new THREE.AmbientLight(0xffffff, 0.6));
const dir = new THREE.DirectionalLight(0xfff0ff, 1.2);
dir.position.set(1, 3, 2);
scene.add(dir);
const fill = new THREE.DirectionalLight(0xd0b0ff, 0.4);
fill.position.set(-2, 1, -1);
scene.add(fill);

// ── load ──────────────────────────────────────────────────────────────────────
let vrm = null;
const clock = new THREE.Clock();
let blinkTimer = 3 + Math.random() * 3;

const vrmPath = await findVRM();

if (!vrmPath) {
  log('VRM not found — check static/ folder and allowed_paths');
} else {
  const loader = new GLTFLoader();
  loader.register(parser => new VRMLoaderPlugin(parser));

  loader.load(
    vrmPath,
    gltf => {
      vrm = gltf.userData.vrm;
      if (!vrm) { log('GLB loaded but no VRM data found — may be wrong format'); return; }
      VRMUtils.removeUnnecessaryJoints(vrm.scene);
      scene.add(vrm.scene);
      vrm.scene.rotation.y = Math.PI;
      log('aiko-chan ✓');
    },
    xhr => {
      if (xhr.total) {
        const pct = Math.round(xhr.loaded / xhr.total * 100);
        log(`loading ${pct}% (${Math.round(xhr.loaded/1024)}KB / ${Math.round(xhr.total/1024)}KB)`);
      } else {
        log(`loading… ${Math.round(xhr.loaded/1024)}KB`);
      }
    },
    err => {
      log(`LOAD ERROR: ${err.message || err}`);
      console.error('[aiko-vrm] full error:', err);
    }
  );
}

// ── expression helpers ────────────────────────────────────────────────────────
function setExpr(name, val = 1.0) {
  if (!vrm?.expressionManager) return;
  ['happy','sad','surprised','relaxed','angry','blink'].forEach(e =>
    vrm.expressionManager.setValue(e, 0));
  if (name && name !== 'neutral')
    vrm.expressionManager.setValue(name, val);
}

window.aikoSetExpression = name => setExpr(name === 'thinking' ? 'relaxed' : name);
window._aikoExprFromText = text => {
  const t = text.toLowerCase();
  let expr = 'neutral';
  if (/!\s|wow|amazing|whoa/.test(t))                              expr = 'surprised';
  else if (/sorry|sad|unfortunate|cannot|can't|don't know/.test(t)) expr = 'sad';
  else if (/hmm|think|let me|consider|wonder/.test(t))              expr = 'relaxed';
  else if (/haha|lol|♥|❤|love|cute|kawaii/.test(t))                expr = 'happy';
  setExpr(expr);
  setTimeout(() => setExpr('neutral'), 5000);
};

// ── animate ───────────────────────────────────────────────────────────────────
function animate() {
  requestAnimationFrame(animate);
  const delta = clock.getDelta();
  const t = clock.elapsedTime;

  if (vrm) {
    vrm.update(delta);
    const head = vrm.humanoid?.getNormalizedBoneNode('head');
    if (head) {
      head.rotation.x = Math.sin(t * 0.5) * 0.04;
      head.rotation.z = Math.sin(t * 0.3) * 0.025;
    }
    blinkTimer -= delta;
    if (blinkTimer <= 0) {
      setExpr('blink', 1);
      setTimeout(() => vrm?.expressionManager?.setValue('blink', 0), 120);
      blinkTimer = 3 + Math.random() * 4;
    }
  }

  controls.update();
  renderer.render(scene, camera);
}
animate();

new ResizeObserver(() => {
  const w = canvas.parentElement.clientWidth;
  const h = canvas.parentElement.clientHeight;
  renderer.setSize(w, h);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}).observe(canvas.parentElement);
</script>
</div>
"""

# ── speech js (tts + asr) ─────────────────────────────────────────────────────
_SPEECH_JS = """
<script>
(function () {
    const TTS_RATE = 1.05, TTS_PITCH = 1.1, TTS_LANG = 'en-US', ASR_LANG = 'en-US';
    let ttsEnabled = true, lastSpoken = '', recognition = null, isListening = false;
    function waitFor(selector, cb, interval=200, maxTries=50) {
        let tries=0;
        const id = setInterval(()=>{ const el=document.querySelector(selector); if(el){clearInterval(id);cb(el);} if(++tries>=maxTries) clearInterval(id); }, interval);
    }
    function stripMarkdown(text) {
        return text.replace(/\U0001f50d Searching:.*/g,'').replace(/\*\*(.*?)\*\*/g,'$1').replace(/\*(.*?)\*/g,'$1').replace(/`{1,3}[^`]*`{1,3}/g,'').replace(/#{1,6}\s/g,'').replace(/\n+/g,' ').trim();
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
        const female=voices.find(v=>v.lang.startsWith('en')&&/female|woman|girl/i.test(v.name))||voices.find(v=>v.lang.startsWith('en'));
        if(female) utt.voice=female;
        window.speechSynthesis.speak(utt);
    }
    function watchChatbot(chatbot) {
        const observer = new MutationObserver(() => {
            const bubbles = chatbot.querySelectorAll('.message.bot,[data-testid="bot"] .md');
            if (!bubbles.length) return;
            const last = bubbles[bubbles.length - 1];
            const text = last.innerText || last.textContent || '';
            speak(text);
            // ← add this
            if (window._aikoExprFromText) window._aikoExprFromText(text);
        });
        observer.observe(chatbot, {childList: true, subtree: true});
    }
    const btnBase = {
        position:'fixed',bottom:'22px',zIndex:'9999',
        background:'rgba(30,15,55,0.85)',
        border:'1.5px solid rgba(155,127,212,0.5)',
        borderRadius:'50%',width:'38px',height:'38px',fontSize:'18px',cursor:'pointer',
        display:'flex',alignItems:'center',justifyContent:'center',
        boxShadow:'0 2px 12px rgba(123,79,212,0.3)',
        backdropFilter:'blur(8px)'
    };
    function buildMicButton() {
        const btn=document.createElement('button');
        btn.id='aiko-mic-btn'; btn.innerHTML='\U0001f3a4'; btn.title='Click to speak';
        Object.assign(btn.style,{...btnBase, right:'60px'});
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
                const submitBtn=document.querySelector('button.submit')||document.querySelector('#component-submit-btn')||document.querySelector('[data-testid="submit-btn"]')||[...document.querySelectorAll('button')].find(b=>b.getAttribute('aria-label')==='Submit'||b.textContent.trim()==='Submit');
                if(submitBtn) submitBtn.click();
            },200);
        };
        recognition.onstart=()=>{isListening=true;btn.innerHTML='\U0001f534';btn.style.background='rgba(180,30,80,0.25)';window.speechSynthesis.cancel();};
        recognition.onend=()=>{isListening=false;btn.innerHTML='\U0001f3a4';btn.style.background='rgba(30,15,55,0.85)';};
        recognition.onerror=(e)=>{console.warn('[aiko-asr]',e.error);isListening=false;btn.innerHTML='\U0001f3a4';btn.style.background='rgba(30,15,55,0.85)';};
        btn.addEventListener('click',()=>{if(isListening){recognition.stop();}else{try{recognition.start();}catch(e){console.warn(e);}}});
    }
    function buildTTSToggle() {
        const btn=document.createElement('button');
        btn.innerHTML='\U0001f50a'; btn.title='Toggle voice';
        Object.assign(btn.style,{...btnBase, right:'12px'});
        btn.addEventListener('click',()=>{ttsEnabled=!ttsEnabled;btn.innerHTML=ttsEnabled?'\U0001f50a':'\U0001f507';if(!ttsEnabled)window.speechSynthesis.cancel();});
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
with gr.Blocks(title="Aiko-chan \U0001f338", css=_CSS) as demo:
    gr.HTML(_SPEECH_JS)

    with gr.Row():
        with gr.Column(scale=6):
            gr.ChatInterface(
                fn=chat,
                title="Aiko-chan \U0001f338",
                chatbot=gr.Chatbot(elem_id="aiko-chatbot"),
            )
        with gr.Column(scale=4, elem_id="aiko-col"):
            gr.HTML(_VRM_VIEWER)

demo.launch(
    server_name="0.0.0.0",
    server_port=7860,
    ssr_mode=False,
    share=False,
    allowed_paths=["static"],   # ← this line is required
)