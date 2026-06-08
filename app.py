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
<div id="aiko-vrm-root" style="width:100%;height:520px;position:relative;background:rgba(10,8,20,0.7);border-radius:16px;overflow:hidden;border:1px solid rgba(155,127,212,0.18);backdrop-filter:blur(18px);">

  <div id="vrm-loading" style="position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:14px;font-family:'Courier New',monospace;z-index:10;background:rgba(10,8,20,0.9);">
    <div style="font-size:11px;letter-spacing:0.4em;color:#9b7fd4;text-shadow:0 0 12px rgba(155,127,212,0.6);">AIKO-CHAN</div>
    <div style="width:140px;height:1px;background:rgba(155,127,212,0.15);overflow:hidden;border-radius:1px;">
      <div id="vrm-load-fill" style="height:100%;width:0%;background:linear-gradient(90deg,#5b2fa8,#9b7fd4);box-shadow:0 0 8px #7b4fd4;transition:width 0.3s;"></div>
    </div>
    <div id="vrm-load-msg" style="font-size:9px;color:rgba(155,127,212,0.45);letter-spacing:0.2em;">loading runtime...</div>
  </div>

  <canvas id="aiko-canvas" style="width:100%;height:100%;display:block;"></canvas>

  <div style="position:absolute;top:10px;right:12px;font-family:'Courier New',monospace;font-size:9px;color:rgba(155,127,212,0.4);letter-spacing:0.15em;">
    <span id="vrm-status" style="margin-right:4px;">&#9679;</span>aiko
  </div>
  <div id="vrm-emotion" style="position:absolute;bottom:10px;left:12px;font-family:'Courier New',monospace;font-size:9px;color:rgba(155,127,212,0.35);letter-spacing:0.15em;text-transform:uppercase;">&#8212;</div>
</div>

<script>
(function() {
  // sequential CDN loader — each waits for previous so THREE is global first
var SCRIPTS = [
    'https://unpkg.com/three@0.163.0/build/three.min.js',
    'https://unpkg.com/three@0.163.0/examples/js/controls/OrbitControls.js',
    'https://unpkg.com/three@0.163.0/examples/js/loaders/GLTFLoader.js',
    'https://unpkg.com/@pixiv/three-vrm@2/lib/three-vrm.js'
];

  function loadScript(i) {
    if (i >= SCRIPTS.length) { initVRM(); return; }
    var s = document.createElement('script');
    s.src = SCRIPTS[i];
    s.onload  = function() { loadScript(i + 1); };
    s.onerror = function() {
      var el = document.getElementById('vrm-load-msg');
      if (el) el.textContent = 'cdn error (script ' + i + ')';
      var st = document.getElementById('vrm-status');
      if (st) st.style.color = '#d45050';
      console.error('[aiko-vrm] failed to load', SCRIPTS[i]);
    };
    document.head.appendChild(s);
  }
  loadScript(0);

  function initVRM() {
    if (typeof THREE === 'undefined') {
      document.getElementById('vrm-load-msg').textContent = 'error: THREE not found';
      return;
    }
    if (typeof THREE_VRM === 'undefined') {
      document.getElementById('vrm-load-msg').textContent = 'error: THREE_VRM not found';
      return;
    }
    if (typeof THREE_VRM.VRMLoaderPlugin === 'undefined') {
      document.getElementById('vrm-load-msg').textContent = 'error: VRMLoaderPlugin not found';
      return;
    }
    
    var root   = document.getElementById('aiko-vrm-root');
    var canvas = document.getElementById('aiko-canvas');
    var loading= document.getElementById('vrm-loading');
    var fill   = document.getElementById('vrm-load-fill');
    var msg    = document.getElementById('vrm-load-msg');
    var status = document.getElementById('vrm-status');
    var emotEl = document.getElementById('vrm-emotion');

    var renderer = new THREE.WebGLRenderer({ canvas: canvas, antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.setClearColor(0x000000, 0);

    var scene  = new THREE.Scene();
    var camera = new THREE.PerspectiveCamera(28, 1, 0.1, 100);
    camera.position.set(0, 1.35, 2.8);

    var controls = new THREE.OrbitControls(camera, canvas);
    controls.target.set(0, 1.1, 0);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.minDistance   = 0.8;
    controls.maxDistance   = 6;
    controls.update();

    scene.add(new THREE.AmbientLight(0xc8b0ff, 0.55));
    var key = new THREE.DirectionalLight(0xffffff, 1.2);
    key.position.set(1, 3, 2); scene.add(key);
    var rim = new THREE.DirectionalLight(0x7b4fd4, 0.45);
    rim.position.set(-2, 1, -1); scene.add(rim);
    var fill2 = new THREE.DirectionalLight(0xd4b0ff, 0.25);
    fill2.position.set(0, -1, 2); scene.add(fill2);
    scene.add(new THREE.GridHelper(10, 20, 0x2a1545, 0x180d2e));

    function resize() {
      var w = root.clientWidth, h = root.clientHeight;
      renderer.setSize(w, h, false);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
    }
    resize();
    new ResizeObserver(resize).observe(root);

    var vrm = null;
    var clock = new THREE.Clock();
    var exprTargets = {}, exprCurrent = {};
    var EXPR_LERP = 6, exprResetTimer = null;
    var blinkTimer = 3.0 + Math.random() * 4.0;
    var blinkPhase = 'wait', blinkT = 0;
    var BLINK_CLOSE = 0.07, BLINK_OPEN = 0.10;
    var t = 0;

    var REST = {
      leftUpperArm:  { x:  0.3, z:  0.3 },
      rightUpperArm: { x:  0.3, z: -0.3 },
      leftLowerArm:  { x: -0.5, z: -0.4 },
      rightLowerArm: { x: -0.5, z:  0.4 },
      leftHand:      { y:  0.4 },
      rightHand:     { y: -0.4 },
    };
    window._REST = REST;

    function applyIdle(dt) {
      if (!vrm || !vrm.humanoid) return;
      t += dt;
      var g = function(n) { return vrm.humanoid.getRawBoneNode(n); };
      var breath = Math.sin(t * 0.83) * 0.013;
      var chest = g('chest'), spine = g('spine');
      if (chest) chest.rotation.x = breath;
      if (spine)  spine.rotation.x = breath * 0.5;
      var hips = g('hips');
      if (hips) {
        hips.rotation.z = Math.sin(t * 0.41) * 0.012;
        hips.rotation.x = Math.sin(t * 0.67) * 0.008;
        hips.position.x = Math.sin(t * 0.41) * 0.003;
      }
      var head = g('head');
      if (head) {
        head.rotation.y = Math.sin(t * 0.31) * 0.055 + Math.sin(t * 1.13) * 0.012;
        head.rotation.z = Math.sin(t * 0.27 + 1.1) * 0.018 + Math.sin(t * 0.71) * 0.006;
        head.rotation.x = Math.sin(t * 0.53) * 0.012;
      }
      var neck = g('neck');
      if (neck && head) {
        neck.rotation.y = head.rotation.y * 0.3;
        neck.rotation.z = head.rotation.z * 0.3;
      }
      var lUA=g('leftUpperArm'),rUA=g('rightUpperArm'),lLA=g('leftLowerArm'),rLA=g('rightLowerArm'),lH=g('leftHand'),rH=g('rightHand');
      if(lUA){lUA.rotation.x=REST.leftUpperArm.x+Math.sin(t*0.47)*0.012;lUA.rotation.z=REST.leftUpperArm.z+Math.sin(t*0.41)*0.008;}
      if(rUA){rUA.rotation.x=REST.rightUpperArm.x+Math.sin(t*0.53+0.9)*0.012;rUA.rotation.z=REST.rightUpperArm.z+Math.sin(t*0.37+0.7)*0.008;}
      if(lLA){lLA.rotation.x=REST.leftLowerArm.x+Math.sin(t*0.61)*0.010;lLA.rotation.z=REST.leftLowerArm.z+Math.sin(t*0.43)*0.006;}
      if(rLA){rLA.rotation.x=REST.rightLowerArm.x+Math.sin(t*0.57+1.4)*0.010;rLA.rotation.z=REST.rightLowerArm.z+Math.sin(t*0.51+0.5)*0.006;}
      if(lH) lH.rotation.y=REST.leftHand.y+Math.sin(t*0.33)*0.008;
      if(rH) rH.rotation.y=REST.rightHand.y+Math.sin(t*0.29+1.2)*0.008;
    }

    function applyBlink(dt) {
      if (!vrm || !vrm.expressionManager) return;
      var em = vrm.expressionManager;
      if (blinkPhase==='wait') {
        blinkTimer-=dt;
        if(blinkTimer<=0){blinkPhase='closing';blinkT=0;}
      } else if (blinkPhase==='closing') {
        blinkT+=dt;
        try{em.setValue('blink',Math.min(blinkT/BLINK_CLOSE,1));}catch(_){}
        if(blinkT>=BLINK_CLOSE){blinkPhase='opening';blinkT=0;}
      } else if (blinkPhase==='opening') {
        blinkT+=dt;
        try{em.setValue('blink',1-Math.min(blinkT/BLINK_OPEN,1));}catch(_){}
        if(blinkT>=BLINK_OPEN){blinkPhase='wait';blinkTimer=3.0+Math.random()*4.0;try{em.setValue('blink',0);}catch(_){}}
      }
    }

    function animate() {
      requestAnimationFrame(animate);
      var dt = Math.min(clock.getDelta(), 0.05);
      controls.update();
      if (vrm) {
        vrm.update(dt);
        var em = vrm.expressionManager;
        if (em) {
          for (var name in exprTargets) {
            var cur = exprCurrent[name]!==undefined ? exprCurrent[name] : 0;
            var next = cur + (exprTargets[name]-cur)*Math.min(1,EXPR_LERP*dt);
            exprCurrent[name] = next;
            if (name!=='blink') try{em.setValue(name,next);}catch(_){}
          }
        }
        applyBlink(dt);
        applyIdle(dt);
      }
      renderer.render(scene, camera);
    }
    animate();

    function setProgress(p, text) {
      fill.style.width = (p*100)+'%';
      if (text) msg.textContent = text;
    }

    var loader = new THREE.GLTFLoader();
    loader.register(function(parser){ return new THREE_VRM.VRMLoaderPlugin(parser); });
    setProgress(0.05, 'fetching model...');

    loader.load('/static/Aiko.vrm',
      function(gltf) {
        setProgress(0.92,'building...');
        vrm = gltf.userData.vrm;
        window._vrm = vrm;
        THREE_VRM.VRMUtils.removeUnnecessaryVertices(vrm.scene);
        vrm.scene.traverse(function(o){if(o.frustumCulled)o.frustumCulled=false;});
        scene.add(vrm.scene);
        if (vrm.expressionManager) {
          vrm.expressionManager.expressions.forEach(function(ex){
            exprTargets[ex.expressionName]=0;
            exprCurrent[ex.expressionName]=0;
          });
        }
        setProgress(1.0,'ready');
        status.style.color='#9b7fd4';
        status.style.textShadow='0 0 8px rgba(155,127,212,0.8)';
        setTimeout(function(){
          loading.style.transition='opacity 0.8s';
          loading.style.opacity='0';
          setTimeout(function(){loading.style.display='none';},800);
        },400);
      },
      function(prog){ var p=prog.total?prog.loaded/prog.total:0; setProgress(0.05+p*0.85,'loading model...'); },
      function(err){ msg.textContent='error: '+(err.message||'unknown'); status.style.color='#d45050'; console.error('[aiko-vrm]',err); }
    );

    window.aikoSetExpression = function(name, intensity) {
      intensity = intensity!==undefined ? intensity : 1.0;
      for(var k in exprTargets){if(k!=='blink')exprTargets[k]=0;}
      if(name&&name!=='neutral') exprTargets[name]=intensity;
      emotEl.textContent=(name&&name!=='neutral')?name+' \xb7 '+Math.round(intensity*100)+'%':'—';
      emotEl.style.color=(name&&name!=='neutral')?'#9b7fd4':'rgba(155,127,212,0.35)';
      clearTimeout(exprResetTimer);
      if(name&&name!=='neutral') exprResetTimer=setTimeout(function(){window.aikoSetExpression('neutral');},4000);
    };

    window.aikoSetViseme = function(viseme, weight) {
      weight=weight!==undefined?weight:1.0;
      var map={A:'aa',I:'ih',U:'ou',E:'ee',O:'oh'};
      var v=map[viseme]||viseme;
      ['aa','ih','ou','ee','oh'].forEach(function(k){exprTargets[k]=0;});
      exprTargets[v]=weight;
    };
  }
})();
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
        const observer=new MutationObserver(()=>{
            const bubbles=chatbot.querySelectorAll('.message.bot,[data-testid="bot"] .md');
            if(!bubbles.length) return;
            const last=bubbles[bubbles.length-1];
            speak(last.innerText||last.textContent||'');
        });
        observer.observe(chatbot,{childList:true,subtree:true});
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
    share=False,   # HF Spaces handles routing; share=True only needed for local tunneling
)