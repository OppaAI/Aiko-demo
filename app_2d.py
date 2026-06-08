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
<div id="aiko-vrm-root" style="width:100%;height:520px;position:relative;background:rgba(10,8,20,0.7);border-radius:16px;overflow:hidden;border:1px solid rgba(155,127,212,0.18);">

  <svg id="aiko-svg" viewBox="0 0 300 520" xmlns="http://www.w3.org/2000/svg"
       style="width:100%;height:100%;display:block;">
    <defs>
      <radialGradient id="bgGlow" cx="50%" cy="60%" r="50%">
        <stop offset="0%" stop-color="#2a0f5e" stop-opacity="0.6"/>
        <stop offset="100%" stop-color="#080612" stop-opacity="0"/>
      </radialGradient>
      <radialGradient id="skinGrad" cx="50%" cy="40%" r="60%">
        <stop offset="0%" stop-color="#fde8d8"/>
        <stop offset="100%" stop-color="#f5c9a8"/>
      </radialGradient>
      <radialGradient id="hairGrad" cx="50%" cy="0%" r="80%">
        <stop offset="0%" stop-color="#c084f5"/>
        <stop offset="100%" stop-color="#7b2fc0"/>
      </radialGradient>
      <filter id="softGlow">
        <feGaussianBlur stdDeviation="3" result="blur"/>
        <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
      </filter>
      <filter id="hairGlow">
        <feGaussianBlur stdDeviation="4" result="blur"/>
        <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
      </filter>
    </defs>

    <!-- background glow -->
    <ellipse cx="150" cy="320" rx="130" ry="160" fill="url(#bgGlow)"/>

    <!-- BODY group — breathes -->
    <g id="body-group">

      <!-- torso / outfit -->
      <g id="torso">
        <!-- body base -->
        <ellipse cx="150" cy="400" rx="58" ry="72" fill="#1a0d35"/>
        <!-- sailor collar -->
        <path d="M110,330 L150,370 L190,330 L175,320 L150,355 L125,320 Z" fill="#9b7fd4" opacity="0.9"/>
        <path d="M125,320 L150,355 L175,320" fill="none" stroke="#c4a8ff" stroke-width="1.5"/>
        <!-- shirt -->
        <rect x="108" y="320" width="84" height="85" rx="8" fill="#140b2e"/>
        <!-- ribbon -->
        <path d="M140,342 L150,352 L160,342 L155,336 L150,344 L145,336 Z" fill="#d45080"/>
        <!-- arms -->
        <ellipse cx="95" cy="360" rx="14" ry="36" fill="#fde8d8" transform="rotate(-8,95,360)"/>
        <ellipse cx="205" cy="360" rx="14" ry="36" fill="#fde8d8" transform="rotate(8,205,360)"/>
        <!-- sleeves -->
        <ellipse cx="95" cy="345" rx="16" ry="22" fill="#140b2e" transform="rotate(-8,95,345)"/>
        <ellipse cx="205" cy="345" rx="16" ry="22" fill="#140b2e" transform="rotate(8,205,345)"/>
        <!-- hands -->
        <ellipse cx="90" cy="393" rx="11" ry="13" fill="#fde8d8"/>
        <ellipse cx="210" cy="393" rx="11" ry="13" fill="#fde8d8"/>
        <!-- skirt -->
        <path d="M108,400 Q80,430 75,475 Q150,490 225,475 Q220,430 192,400 Z" fill="#1e1040"/>
        <path d="M108,400 Q80,430 75,475" fill="none" stroke="#9b7fd4" stroke-width="1" opacity="0.5"/>
        <path d="M192,400 Q220,430 225,475" fill="none" stroke="#9b7fd4" stroke-width="1" opacity="0.5"/>
        <!-- legs -->
        <rect x="120" y="470" width="22" height="45" rx="8" fill="#fde8d8"/>
        <rect x="158" y="470" width="22" height="45" rx="8" fill="#fde8d8"/>
        <!-- stockings -->
        <rect x="120" y="490" width="22" height="28" rx="6" fill="#2a1545"/>
        <rect x="158" y="490" width="22" height="28" rx="6" fill="#2a1545"/>
        <!-- shoes -->
        <ellipse cx="131" cy="518" rx="14" ry="7" fill="#5b2fa8"/>
        <ellipse cx="169" cy="518" rx="14" ry="7" fill="#5b2fa8"/>
      </g>

      <!-- NECK -->
      <rect id="neck" x="141" y="290" width="18" height="32" rx="6" fill="#fde8d8"/>

      <!-- HEAD group -->
      <g id="head-group">
        <!-- hair back -->
        <ellipse cx="150" cy="220" rx="72" ry="78" fill="url(#hairGrad)" filter="url(#hairGlow)"/>
        <!-- long hair sides -->
        <path d="M80,200 Q55,280 65,360 Q85,330 95,310 Q88,260 90,210 Z" fill="#8b35d4" opacity="0.9"/>
        <path d="M220,200 Q245,280 235,360 Q215,330 205,310 Q212,260 210,210 Z" fill="#8b35d4" opacity="0.9"/>
        <!-- hair streaks -->
        <path d="M82,205 Q60,285 68,355" fill="none" stroke="#c084f5" stroke-width="1.5" opacity="0.6"/>
        <path d="M218,205 Q240,285 232,355" fill="none" stroke="#c084f5" stroke-width="1.5" opacity="0.6"/>

        <!-- face -->
        <ellipse id="face" cx="150" cy="228" rx="58" ry="62" fill="url(#skinGrad)"/>

        <!-- hair front / bangs -->
        <path d="M92,190 Q100,145 150,138 Q200,145 208,190 Q190,170 170,168 Q150,162 130,168 Q110,170 92,190 Z" fill="url(#hairGrad)"/>
        <!-- bang strands -->
        <path d="M105,188 Q100,210 108,228" fill="none" stroke="#8b35d4" stroke-width="8" stroke-linecap="round" opacity="0.85"/>
        <path d="M122,178 Q116,205 120,225" fill="none" stroke="#8b35d4" stroke-width="6" stroke-linecap="round" opacity="0.8"/>
        <path d="M178,178 Q184,205 180,225" fill="none" stroke="#8b35d4" stroke-width="6" stroke-linecap="round" opacity="0.8"/>
        <path d="M195,188 Q200,210 192,228" fill="none" stroke="#8b35d4" stroke-width="8" stroke-linecap="round" opacity="0.85"/>
        <!-- hair highlight -->
        <path d="M118,155 Q148,148 175,158" fill="none" stroke="#e8c4ff" stroke-width="3" stroke-linecap="round" opacity="0.5"/>

        <!-- hair accessories — star clips -->
        <polygon points="88,210 91,202 94,210 103,210 97,215 99,223 91,218 83,223 85,215 79,210" fill="#ffd700" opacity="0.9"/>
        <polygon points="212,210 215,202 218,210 227,210 221,215 223,223 215,218 207,223 209,215 203,210" fill="#ffd700" opacity="0.9"/>

        <!-- EYES -->
        <g id="eyes">
          <!-- eye whites / shadow -->
          <ellipse cx="126" cy="228" rx="16" ry="14" fill="white" opacity="0.9"/>
          <ellipse cx="174" cy="228" rx="16" ry="14" fill="white" opacity="0.9"/>

          <!-- iris left -->
          <ellipse id="iris-l" cx="126" cy="230" rx="11" ry="12" fill="#7b2fc0"/>
          <ellipse cx="126" cy="230" rx="8" ry="9" fill="#4a1a8a"/>
          <ellipse cx="126" cy="230" rx="4" ry="5" fill="#1a0635"/>
          <!-- iris right -->
          <ellipse id="iris-r" cx="174" cy="230" rx="11" ry="12" fill="#7b2fc0"/>
          <ellipse cx="174" cy="230" rx="8" ry="9" fill="#4a1a8a"/>
          <ellipse cx="174" cy="230" rx="4" ry="5" fill="#1a0635"/>

          <!-- eye shine -->
          <ellipse cx="121" cy="224" rx="3.5" ry="3" fill="white" opacity="0.9"/>
          <ellipse cx="169" cy="224" rx="3.5" ry="3" fill="white" opacity="0.9"/>
          <ellipse cx="130" cy="226" rx="1.5" ry="1.5" fill="white" opacity="0.6"/>
          <ellipse cx="178" cy="226" rx="1.5" ry="1.5" fill="white" opacity="0.6"/>

          <!-- upper lashes -->
          <path d="M110,220 Q118,214 142,218" fill="none" stroke="#2a0845" stroke-width="2.5" stroke-linecap="round"/>
          <path d="M158,218 Q182,214 190,220" fill="none" stroke="#2a0845" stroke-width="2.5" stroke-linecap="round"/>

          <!-- blink overlays — hidden by default -->
          <ellipse id="blink-l" cx="126" cy="228" rx="16" ry="1" fill="#fde8d8" opacity="0" transform-origin="126 228"/>
          <ellipse id="blink-r" cx="174" cy="228" rx="16" ry="1" fill="#fde8d8" opacity="0" transform-origin="174 228"/>
        </g>

        <!-- eyebrows -->
        <g id="brows">
          <path id="brow-l" d="M110,212 Q126,206 142,210" fill="none" stroke="#6b25a0" stroke-width="3" stroke-linecap="round"/>
          <path id="brow-r" d="M158,210 Q174,206 190,212" fill="none" stroke="#6b25a0" stroke-width="3" stroke-linecap="round"/>
        </g>

        <!-- blush -->
        <ellipse id="blush-l" cx="108" cy="242" rx="14" ry="8" fill="#ffb0c8" opacity="0.35"/>
        <ellipse id="blush-r" cx="192" cy="242" rx="14" ry="8" fill="#ffb0c8" opacity="0.35"/>

        <!-- MOUTH -->
        <g id="mouth-group">
          <!-- happy default -->
          <path id="mouth-happy" d="M136,258 Q150,270 164,258" fill="none" stroke="#c06080" stroke-width="2.5" stroke-linecap="round"/>
          <!-- surprised — hidden -->
          <ellipse id="mouth-surprised" cx="150" cy="262" rx="8" ry="10" fill="#8a2040" opacity="0"/>
          <!-- sad — hidden -->
          <path id="mouth-sad" d="M136,266 Q150,256 164,266" fill="none" stroke="#c06080" stroke-width="2.5" stroke-linecap="round" opacity="0"/>
        </g>

        <!-- cat ear blush (hidden, shown on happy) -->
        <ellipse id="blush-l2" cx="108" cy="242" rx="14" ry="8" fill="#ff80a0" opacity="0"/>
        <ellipse id="blush-r2" cx="192" cy="242" rx="14" ry="8" fill="#ff80a0" opacity="0"/>

      </g><!-- end head-group -->
    </g><!-- end body-group -->

    <!-- floating particles -->
    <g id="particles" opacity="0.5">
      <circle class="particle" cx="60" cy="150" r="2" fill="#9b7fd4"/>
      <circle class="particle" cx="240" cy="180" r="1.5" fill="#c084f5"/>
      <circle class="particle" cx="45" cy="300" r="1" fill="#7b4fd4"/>
      <circle class="particle" cx="255" cy="120" r="2" fill="#9b7fd4"/>
      <circle class="particle" cx="270" cy="350" r="1.5" fill="#c084f5"/>
      <circle class="particle" cx="30" cy="400" r="1" fill="#7b4fd4"/>
    </g>

    <!-- status label -->
    <text x="150" y="18" text-anchor="middle" font-family="'Courier New',monospace"
          font-size="9" fill="#9b7fd4" letter-spacing="4" opacity="0.7">AIKO-CHAN</text>
    <text id="emotion-label" x="150" y="510" text-anchor="middle" font-family="'Courier New',monospace"
          font-size="9" fill="rgba(155,127,212,0.45)" letter-spacing="2">idle</text>
  </svg>

  <script>
  (function(){
    var t = 0;
    var blinkTimer = 3 + Math.random()*3;
    var blinkOpen = true;
    var currentExpr = 'neutral';

    var bodyGroup  = document.getElementById('body-group');
    var headGroup  = document.getElementById('head-group');
    var blinkL     = document.getElementById('blink-l');
    var blinkR     = document.getElementById('blink-r');
    var browL      = document.getElementById('brow-l');
    var browR      = document.getElementById('brow-r');
    var blushL2    = document.getElementById('blush-l2');
    var blushR2    = document.getElementById('blush-r2');
    var mouthHappy = document.getElementById('mouth-happy');
    var mouthSad   = document.getElementById('mouth-sad');
    var mouthSurp  = document.getElementById('mouth-surprised');
    var emotLabel  = document.getElementById('emotion-label');
    var irisL      = document.getElementById('iris-l');
    var irisR      = document.getElementById('iris-r');

    var particles  = document.querySelectorAll('.particle');
    var partPhase  = Array.from(particles).map(function(_,i){ return i*1.1; });

    function setAttr(el, attr, val){ if(el) el.setAttribute(attr, val); }
    function setStyle(el, prop, val){ if(el) el.style[prop] = val; }

    function applyExpression(expr){
      currentExpr = expr;
      if(emotLabel) emotLabel.textContent = expr;
      // reset
      setAttr(mouthHappy,'opacity','1');
      setAttr(mouthSad,'opacity','0');
      setAttr(mouthSurp,'opacity','0');
      setAttr(blushL2,'opacity','0');
      setAttr(blushR2,'opacity','0');
      setAttr(browL,'d','M110,212 Q126,206 142,210');
      setAttr(browR,'d','M158,210 Q174,206 190,212');
      setAttr(irisL,'ry','12');
      setAttr(irisR,'ry','12');

      if(expr === 'happy'){
        setAttr(browL,'d','M110,209 Q126,203 142,207');
        setAttr(browR,'d','M158,207 Q174,203 190,209');
        setAttr(blushL2,'opacity','0.4');
        setAttr(blushR2,'opacity','0.4');
      } else if(expr === 'surprised'){
        setAttr(browL,'d','M110,207 Q126,200 142,205');
        setAttr(browR,'d','M158,205 Q174,200 190,207');
        setAttr(mouthHappy,'opacity','0');
        setAttr(mouthSurp,'opacity','1');
        setAttr(irisL,'ry','14');
        setAttr(irisR,'ry','14');
      } else if(expr === 'sad'){
        setAttr(browL,'d','M110,212 Q126,216 142,213');
        setAttr(browR,'d','M158,213 Q174,216 190,212');
        setAttr(mouthHappy,'opacity','0');
        setAttr(mouthSad,'opacity','1');
      } else if(expr === 'thinking'){
        setAttr(browL,'d','M110,210 Q126,206 142,211');
        setAttr(browR,'d','M158,207 Q174,203 190,210');
      }
    }

    function tick(){
      t += 0.016;
      // body bob
      var bob = Math.sin(t*0.9)*3;
      var breathX = Math.sin(t*0.83)*0.012;
      if(bodyGroup) bodyGroup.setAttribute('transform',
        'translate(0,'+bob.toFixed(2)+')');
      // head slight sway
      var headSway = Math.sin(t*0.4)*1.5;
      if(headGroup) headGroup.setAttribute('transform',
        'translate('+headSway.toFixed(2)+',0)');

      // blink
      blinkTimer -= 0.016;
      if(blinkTimer <= 0){
        blinkOpen = !blinkOpen;
        blinkTimer = blinkOpen ? (3+Math.random()*4) : 0.1;
        var ry = blinkOpen ? '1' : '14';
        var op = blinkOpen ? '0' : '1';
        setAttr(blinkL,'ry',ry); setAttr(blinkL,'opacity',op);
        setAttr(blinkR,'ry',ry); setAttr(blinkR,'opacity',op);
      }

      // particles float
      particles.forEach(function(p, i){
        partPhase[i] += 0.008;
        var cy = parseFloat(p.getAttribute('data-base-cy')||p.getAttribute('cy'));
        if(!p.getAttribute('data-base-cy')) p.setAttribute('data-base-cy', cy);
        p.setAttribute('cy', (cy + Math.sin(partPhase[i])*12).toFixed(1));
        p.setAttribute('opacity', (0.2 + Math.sin(partPhase[i]*0.7+1)*0.3).toFixed(2));
      });

      requestAnimationFrame(tick);
    }
    tick();

    // public API — same interface as VRM version
    window.aikoSetExpression = function(name){
      applyExpression(name||'neutral');
    };

    // auto-expression from chat: hook into the same MutationObserver
    window._aikoExprFromText = function(text){
      var t = text.toLowerCase();
      if(/\!\s|wow|amazing|whoa/.test(t)) applyExpression('surprised');
      else if(/sorry|sad|unfortunate|cannot|can't|don't know/.test(t)) applyExpression('sad');
      else if(/hmm|think|let me|consider|wonder/.test(t)) applyExpression('thinking');
      else if(/haha|lol|\u2665|\u2764|love|cute|kawaii/.test(t)) applyExpression('happy');
      else applyExpression('neutral');
      setTimeout(function(){ applyExpression('neutral'); }, 5000);
    };
  })();
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
    share=False,   # HF Spaces handles routing; share=True only needed for local tunneling
)