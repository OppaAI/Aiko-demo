from __future__ import annotations

import html
import os
from pathlib import Path
from urllib.parse import quote


def resolve_vrm_path() -> Path:
    """Return the configured VRM path, preferring the Space's static/Aiko.vrm."""
    candidates = [
        Path(os.getenv("AIKO_VRM_PATH", "static/Aiko.vrm")),
        Path("assets/Aiko.vrm"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    return candidates[0].resolve()


def gradio_file_urls(path: Path) -> list[str]:
    """Build Gradio file-serving URL candidates for an allowed local path."""
    encoded_path = quote(path.as_posix(), safe="/:")
    return [f"/gradio_api/file={encoded_path}", f"/file={encoded_path}"]


def gradio_file_url(path: Path) -> str:
    """Return the preferred Gradio file-serving URL for compatibility callers."""
    return gradio_file_urls(path)[0]


def avatar_html(vrm_urls: str | list[str]) -> str:
    """Return an iframe containing the Three/VRM viewer.

    Camera is framed to a half-body shot (waist-up). The iframe exposes a
    postMessage API for expression, viseme, ttsText, and duration control.
    Caption bar at the bottom streams the speech text during audio playback.

    postMessage API (JSON string or object):
      { expression: str, intensity?: float }        — set face expression
      { ttsText: str, duration?: float }            — set lip-sync + caption text
      { speaking: bool }                            — force speaking state
      { viseme: str, weight?: float }               — direct viseme override
    """
    if isinstance(vrm_urls, str):
        vrm_urls = [vrm_urls]

    srcdoc = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <style>
    * {{ box-sizing: border-box; }}
    html, body {{
      margin: 0;
      width: 100%;
      height: 100%;
      overflow: hidden;
      background: radial-gradient(circle at 50% 12%, #22183f 0, #0b0a14 48%, #050509 100%);
      color: #c8b8e8;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
    }}
    #wrap {{
        position: fixed;
        inset: 0;
        width: 100vw !important;
        height: 100vh !important;
        max-height: 100vh !important;
        overflow: hidden !important;
    }}
    canvas {{
        display: block;
        width: 100% !important;
        height: 100% !important;
        max-width: 100vw !important;
        max-height: 100vh !important;
    }}
    /* HUD: minimal top status only */
    #hud {{
      position: fixed;
      inset: 0;
      pointer-events: none;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      padding: 14px 18px 70px;
      background: linear-gradient(180deg, rgba(5,5,10,.45), transparent 20%, transparent 72%, rgba(5,5,10,.55));
    }}
    #top {{ display: flex; justify-content: space-between; align-items: center; gap: 12px; }}
    #status {{ display: flex; align-items: center; gap: 8px; color: #8b7ab6; font-size: 11px; }}
    #dot {{ width: 8px; height: 8px; border-radius: 999px; background: #4b3a79; box-shadow: 0 0 10px rgba(155,127,212,.2); }}
    #dot.speaking {{ background: #d68cff; box-shadow: 0 0 16px rgba(214,140,255,.9); animation: pulse .6s infinite; }}
    #emotion {{ letter-spacing: .16em; text-transform: uppercase; font-size: 11px; color: #7867a3; }}
    /* Caption bar — bottom of the canvas, left side so it doesn't clash with chat overlay */
    #caption-bar {{
      position: fixed;
      bottom: 0;
      left: 0;
      right: 40%;
      min-height: 50px;
      max-height: 108px;
      padding: 10px 20px 14px 18px;
      display: flex;
      align-items: flex-end;
      background: linear-gradient(0deg, rgba(5,5,10,.90) 0%, transparent 100%);
      pointer-events: none;
      z-index: 8;
      transition: opacity .3s;
    }}
    #caption-bar.hidden {{ opacity: 0; }}
    #caption-text {{
      color: #ecdeff;
      font-size: 13px;
      line-height: 1.55;
      text-shadow: 0 1px 6px rgba(0,0,0,0.95), 0 0 20px rgba(110,60,200,.55);
      letter-spacing: .01em;
      max-width: 100%;
      word-break: break-word;
    }}
    #loader {{
      position: fixed; inset: 0; display: grid; place-content: center; gap: 18px; text-align: center;
      background: #080810; z-index: 10; transition: opacity .45s ease;
    }}
    #loader.fade {{ opacity: 0; pointer-events: none; }}
    #loader h1 {{ margin: 0; color: #b39cff; letter-spacing: .28em; text-transform: uppercase; font-size: 22px; }}
    #loader p  {{ margin: 0; color: #69578f; font-size: 11px; letter-spacing: .16em; }}
    @keyframes pulse {{ 0%,100% {{ opacity: 1 }} 50% {{ opacity: .45 }} }}
  </style>
  <script type="importmap">
  {{
    "imports": {{
      "three": "https://cdn.jsdelivr.net/npm/three@0.170.0/build/three.module.js",
      "three/addons/": "https://cdn.jsdelivr.net/npm/three@0.170.0/examples/jsm/",
      "@pixiv/three-vrm": "https://cdn.jsdelivr.net/npm/@pixiv/three-vrm@3/lib/three-vrm.module.min.js"
    }}
  }}
  </script>
</head>
<body>
  <div id="wrap"><canvas id="canvas"></canvas></div>
  <div id="hud">
    <div id="top">
      <div id="emotion">neutral</div>
      <div id="status"><span id="dot"></span><span id="status-text">idle</span></div>
    </div>
  </div>
  <!-- Closed-caption bar: streams assistant text during audio playback -->
  <div id="caption-bar" class="hidden">
    <div id="caption-text"></div>
  </div>
  <div id="loader"><h1>🌸 Aiko</h1><p id="load-msg">loading VRM…</p></div>
  <script type="module">
    import * as THREE from 'three';
    import {{ OrbitControls }} from 'three/addons/controls/OrbitControls.js';
    import {{ GLTFLoader }} from 'three/addons/loaders/GLTFLoader.js';
    import {{ VRMLoaderPlugin, VRMUtils }} from '@pixiv/three-vrm';

    // ── Hard-lock this iframe's document height ──────────────────────────────
    document.documentElement.style.setProperty('height', '100vh', 'important');
    document.documentElement.style.setProperty('overflow', 'hidden', 'important');
    document.body.style.setProperty('height', '100vh', 'important');
    document.body.style.setProperty('overflow', 'hidden', 'important');
    document.body.style.setProperty('max-height', '100vh', 'important');

    const RAW_VRM_URLS  = {vrm_urls!r};
    const VISEME_MAP    = {{ A: 'aa', I: 'ih', U: 'ou', E: 'ee', O: 'oh' }};
    const VISEME_PRESETS = ['aa', 'ih', 'ou', 'ee', 'oh'];
    const TEXT_VISEME_MAP = {{
      a: 'aa', á: 'aa', à: 'aa', â: 'aa', ä: 'aa', あ: 'aa', ア: 'aa', か: 'aa', カ: 'aa', さ: 'aa', サ: 'aa', た: 'aa', タ: 'aa', な: 'aa', ナ: 'aa', は: 'aa', ハ: 'aa', ま: 'aa', マ: 'aa', や: 'aa', ヤ: 'aa', ら: 'aa', ラ: 'aa', わ: 'aa', ワ: 'aa',
      i: 'ih', í: 'ih', ì: 'ih', î: 'ih', ï: 'ih', y: 'ih', い: 'ih', イ: 'ih', き: 'ih', キ: 'ih', し: 'ih', シ: 'ih', ち: 'ih', チ: 'ih', に: 'ih', ニ: 'ih', ひ: 'ih', ヒ: 'ih', み: 'ih', ミ: 'ih', り: 'ih', リ: 'ih',
      u: 'ou', ú: 'ou', ù: 'ou', û: 'ou', ü: 'ou', う: 'ou', ウ: 'ou', く: 'ou', ク: 'ou', す: 'ou', ス: 'ou', つ: 'ou', ツ: 'ou', ぬ: 'ou', ヌ: 'ou', ふ: 'ou', フ: 'ou', む: 'ou', ム: 'ou', ゆ: 'ou', ユ: 'ou', る: 'ou', ル: 'ou',
      e: 'ee', é: 'ee', è: 'ee', ê: 'ee', ë: 'ee', え: 'ee', エ: 'ee', け: 'ee', ケ: 'ee', せ: 'ee', セ: 'ee', て: 'ee', テ: 'ee', ね: 'ee', ネ: 'ee', へ: 'ee', ヘ: 'ee', め: 'ee', メ: 'ee', れ: 'ee', レ: 'ee',
      o: 'oh', ó: 'oh', ò: 'oh', ô: 'oh', ö: 'oh', お: 'oh', オ: 'oh', こ: 'oh', コ: 'oh', そ: 'oh', ソ: 'oh', と: 'oh', ト: 'oh', の: 'oh', ノ: 'oh', ほ: 'oh', ホ: 'oh', も: 'oh', モ: 'oh', よ: 'oh', ヨ: 'oh', ろ: 'oh', ロ: 'oh', を: 'oh', ヲ: 'oh', ん: 'oh', ン: 'oh',
    }};

    function withTrailingSlash(url) {{ return url.endsWith('/') ? url : url + '/'; }}
    function buildVrmUrls(rawUrls) {{
      const urls = [];
      let parentHref = null, parentOrigin = null;
      try {{ parentHref = parent.location.href; parentOrigin = parent.location.origin; }}
      catch (_) {{ parentHref = window.location.href; parentOrigin = window.location.origin; }}
      for (const raw of rawUrls) {{
        if (!raw) continue;
        try {{
          if (/^https?:\/\//.test(raw)) {{ urls.push(raw); }}
          else {{
            urls.push(new URL(raw, parentOrigin).href);
            urls.push(new URL(raw.replace(/^\//, ''), withTrailingSlash(parentHref)).href);
          }}
        }} catch (err) {{ console.warn('[aiko-vrm] bad VRM URL', raw, err); }}
      }}
      return [...new Set(urls)];
    }}

    const VRM_URLS = buildVrmUrls(RAW_VRM_URLS);
    const canvas   = document.getElementById('canvas');
    const renderer = new THREE.WebGLRenderer({{ canvas, antialias: true, alpha: true }});
    renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    renderer.outputColorSpace = THREE.SRGBColorSpace;

    const scene  = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(22, 1, 0.1, 100);
    camera.position.set(0.00, 1.18, 2.5);
    const controls = new OrbitControls(camera, canvas);
    controls.target.set(0.00, 1.15, 0);
    controls.enableDamping = true;
    controls.enablePan     = false;
    controls.minDistance   = 1.0;
    controls.maxDistance   = 3.2;

    scene.add(new THREE.HemisphereLight(0xded4ff, 0x21182f, 2.4));
    const key = new THREE.DirectionalLight(0xffffff, 2.7);
    key.position.set(1.8, 3.0, 2.5);
    scene.add(key);
    const rim = new THREE.DirectionalLight(0x9b7cff, 1.5);
    rim.position.set(-2.5, 1.4, -1.2);
    scene.add(rim);

    let vrm = null;
    let mouth = 0;
    let smoothedAudioMouth = 0;
    let speaking = false;
    const clock = new THREE.Clock();
    let blinkTimer = 3.0 + Math.random() * 4.0;
    let blinkPhase = 'wait';
    let blinkT = 0;
    const BLINK_CLOSE_DUR = 0.07;
    const BLINK_OPEN_DUR  = 0.10;
    let exprResetTimer = null;
    const EXPR_RESET_DELAY = 4000;
    let idleTime = 0;
    let speechText     = '';
    let speechVisemes  = [];
    let speechStartedAt = 0;
    let speechDuration = 0;

    const REST = window._REST = {{
      leftUpperArm:  {{ x:  0.02, y: 0.0, z: -1.28 }},
      rightUpperArm: {{ x:  0.02, y: 0.0, z:  1.28 }},
      leftLowerArm:  {{ x: -0.12, y: 0.0, z: -0.08 }},
      rightLowerArm: {{ x: -0.12, y: 0.0, z:  0.08 }},
      leftHand:      {{ x:  0.0,  y: 0.08, z:  0.0 }},
      rightHand:     {{ x:  0.0,  y:-0.08, z:  0.0 }},
    }};

    const dot         = document.getElementById('dot');
    const statusText  = document.getElementById('status-text');
    const emotionEl   = document.getElementById('emotion');
    const captionBar  = document.getElementById('caption-bar');
    const captionText = document.getElementById('caption-text');

    // ── Caption streaming ─────────────────────────────────────────────────────
    // Paces word-by-word reveal proportional to audio duration.
    let captionWords = [];
    let captionIdx   = 0;
    let captionTimer = null;

    function startCaption(text) {{
      clearInterval(captionTimer);
      captionWords = text.trim().split(/\s+/).filter(Boolean);
      captionIdx   = 0;
      captionText.textContent = '';
      captionBar.classList.remove('hidden');
      if (!captionWords.length) return;

      const totalWords   = captionWords.length;
      const totalSeconds = (lastAudio && lastAudio.duration > 0)
        ? lastAudio.duration
        : Math.max(2, totalWords * 0.38);
      const msPerWord = (totalSeconds * 1000) / totalWords;

      captionTimer = setInterval(() => {{
        if (captionIdx >= captionWords.length) {{
          clearInterval(captionTimer);
          setTimeout(() => {{ captionBar.classList.add('hidden'); }}, 1800);
          return;
        }}
        const windowEnd   = captionIdx + 1;
        const windowStart = Math.max(0, windowEnd - 12);
        captionText.textContent = captionWords.slice(windowStart, windowEnd).join(' ');
        captionIdx++;
      }}, msPerWord);
    }}

    function stopCaption() {{
      clearInterval(captionTimer);
      setTimeout(() => captionBar.classList.add('hidden'), 1200);
    }}

    // ─────────────────────────────────────────────────────────────────────────
    function nextBlinkWait() {{ return 3.0 + Math.random() * 4.0; }}
    function expressionNames() {{
      return (vrm?.expressionManager?.expressions ?? [])
        .map(e => e.expressionName ?? e.name).filter(Boolean);
    }}
    function hasExpression(name) {{ return expressionNames().includes(name); }}
    function safeSetExpression(name, weight) {{
      try {{ vrm?.expressionManager?.setValue(name, weight); }} catch (_) {{}}
    }}

    let lastW = 0, lastH = 0;
    function resize() {{
      const w = Math.max(1, Math.min(window.screen.width,  canvas.clientWidth  || window.innerWidth));
      const h = Math.max(1, Math.min(window.screen.height, canvas.clientHeight || window.innerHeight));
      if (w === lastW && h === lastH) return;
      lastW = w; lastH = h;
      renderer.setSize(w, h, false);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
    }}
    addEventListener('resize', resize);

    function setExpression(name, weight = 1) {{
      if (!vrm?.expressionManager) return;
      for (const k of ['happy', 'relaxed', 'angry', 'sad', 'surprised']) {{
        safeSetExpression(k, k === name ? weight : 0);
      }}
      emotionEl.textContent = name || 'neutral';
    }}

    function setMouth(weight, viseme = 'aa') {{
      if (!vrm) return;
      const clamped = Math.max(0, Math.min(1, Number(weight) || 0));
      const preset  = VISEME_MAP[viseme] ?? viseme ?? 'aa';
      let usedExpression = false;
      if (vrm.expressionManager) {{
        for (const k of VISEME_PRESETS) {{
          if (hasExpression(k)) {{
            vrm.expressionManager.setValue(k, k === preset ? clamped : 0);
            usedExpression = true;
          }}
        }}
        try {{
          const em = vrm.expressionManager;
          if (em._expressions) {{
            em._expressions.forEach(expr => expr.applyWeight({{ multiplier: 1 }}));
          }}
        }} catch (_) {{}}
      }}
      if (!usedExpression) {{
        const jaw = vrm.humanoid?.getNormalizedBoneNode?.('jaw') || vrm.humanoid?.getRawBoneNode?.('jaw');
        if (jaw) jaw.rotation.x = clamped * 0.5;
      }}
    }}

    function clearMouth() {{ setMouth(0, 'aa'); }}

    function setSpeaking(active) {{
      speaking = Boolean(active);
      dot.className = speaking ? 'speaking' : '';
      statusText.textContent = speaking ? 'speaking' : 'idle';
      setExpression(speaking ? 'happy' : 'relaxed', speaking ? 0.55 : 0.25);
      if (!speaking) {{ clearMouth(); stopCaption(); }}
    }}

    function estimateSpeechDuration(text, requestedDuration = null) {{
      const explicit = Number(requestedDuration);
      if (Number.isFinite(explicit) && explicit > 0) return explicit;
      if (lastAudio && Number.isFinite(lastAudio.duration) && lastAudio.duration > 0) return lastAudio.duration;
      return Math.max(1.0, Math.min(12, text.length * 0.075));
    }}

    function textToVisemes(text) {{
      const tokens = [];
      let lastViseme = 'aa';
      for (const rawChar of String(text || '').toLowerCase()) {{
        const viseme = TEXT_VISEME_MAP[rawChar];
        if (viseme) {{
          lastViseme = viseme;
          tokens.push({{ viseme, weight: 0.88 }});
        }} else if (/[,.;:!?。！？、\s]/.test(rawChar)) {{
          tokens.push({{ viseme: lastViseme, weight: 0.08 }});
        }} else if (/[bcdfghjklmnpqrstvwxz]/.test(rawChar)) {{
          tokens.push({{ viseme: lastViseme, weight: 0.28 }});
        }}
      }}
      return tokens.length ? tokens : [{{ viseme: 'aa', weight: 0.25 }}];
    }}

    function setSpeechText(text, duration = null) {{
      const nextText = String(text || '').trim();
      if (!nextText) return;
      speechText      = nextText;
      speechVisemes   = textToVisemes(speechText);
      speechDuration  = estimateSpeechDuration(speechText, duration);
      speechStartedAt = performance.now();
      startCaption(speechText);
    }}

    function currentTextMouth(now) {{
      if (!speechVisemes.length) return null;
      const audioDuration = lastAudio && Number.isFinite(lastAudio.duration) && lastAudio.duration > 0
        ? lastAudio.duration : speechDuration;
      const duration  = Math.max(0.25, audioDuration || speechDuration || 1);
      const elapsed   = lastAudio && !lastAudio.paused
        ? lastAudio.currentTime
        : (now - speechStartedAt) / 1000;
      const progress  = Math.max(0, Math.min(0.999, elapsed / duration));
      const index     = Math.min(speechVisemes.length - 1, Math.floor(progress * speechVisemes.length));
      const token     = speechVisemes[index];
      const syllablePhase = Math.sin(progress * speechVisemes.length * Math.PI);
      return {{
        viseme: token.viseme,
        weight: Math.max(0, Math.min(1, token.weight * (0.55 + Math.abs(syllablePhase) * 0.45))),
      }};
    }}

    function getBone(name) {{
      const h = vrm?.humanoid;
      if (!h) return null;
      return h.getRawBoneNode?.(name) || h.getNormalizedBoneNode?.(name) || null;
    }}

    function applyIdle(dt) {{
      if (!vrm?.humanoid) return;
      idleTime += dt;
      const breath = Math.sin(idleTime * 0.83) * 0.013;
      const chest  = getBone('chest');
      const spine  = getBone('spine');
      if (chest) chest.rotation.x = breath;
      if (spine) spine.rotation.x = breath * 0.5;
      const hips = getBone('hips');
      if (hips) {{
        hips.rotation.z = Math.sin(idleTime * 0.41) * 0.012;
        hips.rotation.x = Math.sin(idleTime * 0.67) * 0.008;
        hips.position.x = Math.sin(idleTime * 0.41) * 0.003;
      }}
      const head = getBone('head');
      if (head) {{
        head.rotation.y = Math.sin(idleTime * 0.31) * 0.055 + Math.sin(idleTime * 1.13) * 0.012;
        head.rotation.z = Math.sin(idleTime * 0.27 + 1.1) * 0.018 + Math.sin(idleTime * 0.71) * 0.006;
        head.rotation.x = Math.sin(idleTime * 0.53) * 0.012;
      }}
      if (!speaking) {{
        safeSetExpression('relaxed', 0.20 + Math.sin(idleTime * 0.37) * 0.035);
        safeSetExpression('happy',   Math.max(0, Math.sin(idleTime * 0.19 - 0.8)) * 0.035);
      }}
      const neck = getBone('neck');
      if (neck && head) {{
        neck.rotation.y = head.rotation.y * 0.3;
        neck.rotation.z = head.rotation.z * 0.3;
      }}
      const lUA = getBone('leftUpperArm'),  rUA = getBone('rightUpperArm');
      const lLA = getBone('leftLowerArm'),  rLA = getBone('rightLowerArm');
      const lH  = getBone('leftHand'),      rH  = getBone('rightHand');
      if (lUA) {{ lUA.rotation.x = REST.leftUpperArm.x  + Math.sin(idleTime * 0.47) * 0.010; lUA.rotation.y = REST.leftUpperArm.y  + Math.sin(idleTime * 0.33) * 0.006; lUA.rotation.z = REST.leftUpperArm.z  + Math.sin(idleTime * 0.41) * 0.008; }}
      if (rUA) {{ rUA.rotation.x = REST.rightUpperArm.x + Math.sin(idleTime * 0.53 + 0.9) * 0.010; rUA.rotation.y = REST.rightUpperArm.y + Math.sin(idleTime * 0.35 + 0.4) * 0.006; rUA.rotation.z = REST.rightUpperArm.z + Math.sin(idleTime * 0.37 + 0.7) * 0.008; }}
      if (lLA) {{ lLA.rotation.x = REST.leftLowerArm.x  + Math.sin(idleTime * 0.61) * 0.008; lLA.rotation.y = REST.leftLowerArm.y; lLA.rotation.z = REST.leftLowerArm.z  + Math.sin(idleTime * 0.43) * 0.004; }}
      if (rLA) {{ rLA.rotation.x = REST.rightLowerArm.x + Math.sin(idleTime * 0.57 + 1.4) * 0.008; rLA.rotation.y = REST.rightLowerArm.y; rLA.rotation.z = REST.rightLowerArm.z + Math.sin(idleTime * 0.51 + 0.5) * 0.004; }}
      if (lH)  {{ lH.rotation.x  = REST.leftHand.x;  lH.rotation.y  = REST.leftHand.y  + Math.sin(idleTime * 0.33) * 0.008; lH.rotation.z = REST.leftHand.z; }}
      if (rH)  {{ rH.rotation.x  = REST.rightHand.x; rH.rotation.y  = REST.rightHand.y + Math.sin(idleTime * 0.29 + 1.2) * 0.008; rH.rotation.z = REST.rightHand.z; }}
    }}

    // ── Idle gesture state machine ────────────────────────────────────────────
    let gestureState    = 'none';
    let gestureT        = 0;
    let gestureDuration = 0;
    let gestureCooldown = 4 + Math.random() * 6;
    let gestureTarget   = null;
    const GESTURES = ['lookAround', 'sideGlance', 'meetGaze', 'curiousTilt', 'shiftWeight', 'hairTuck', 'stretchNeck'];
    const GESTURE_DURATION = {{
      lookAround: 3.2, sideGlance: 2.2, meetGaze: 2.8,
      curiousTilt: 2.4, shiftWeight: 3.2, hairTuck: 2.7, stretchNeck: 2.6,
    }};

    function pickGesture() {{
      const g = GESTURES[Math.floor(Math.random() * GESTURES.length)];
      gestureState    = g;
      gestureT        = 0;
      gestureDuration = GESTURE_DURATION[g] ?? 2.5;
      const side = Math.random() < 0.5 ? -1 : 1;
      gestureTarget = {{
        lookAround: side * (0.22 + Math.random() * 0.18),
        sideGlance: side * (0.16 + Math.random() * 0.10),
        curiousTilt: side * (0.08 + Math.random() * 0.07),
        hairSide: side,
      }};
    }}

    function easeInOutSine(t) {{ return -(Math.cos(Math.PI * t) - 1) / 2; }}
    function holdCurve(progress, inPortion = 0.28, outPortion = 0.30) {{
      if (progress < inPortion) return easeInOutSine(progress / inPortion);
      if (progress > 1 - outPortion) return easeInOutSine((1 - progress) / outPortion);
      return 1;
    }}

    function applyGestures(dt) {{
      if (!vrm?.humanoid) return;
      if (speaking) {{ gestureState = 'none'; return; }}
      if (gestureState === 'none') {{
        gestureCooldown -= dt;
        if (gestureCooldown <= 0) {{ pickGesture(); gestureCooldown = 4 + Math.random() * 6; }}
        return;
      }}
      gestureT += dt;
      const progress  = Math.min(1, gestureT / gestureDuration);
      const intensity = Math.sin(progress * Math.PI);
      const eased     = easeInOutSine(progress);
      const held      = holdCurve(progress);
      const head = getBone('head'), neck = getBone('neck');
      const lUA  = getBone('leftUpperArm'), lLA = getBone('leftLowerArm'), lH = getBone('leftHand');
      const rUA  = getBone('rightUpperArm'), rLA = getBone('rightLowerArm'), rH = getBone('rightHand');
      const spine = getBone('spine'), hips = getBone('hips');
      switch (gestureState) {{
        case 'lookAround':
          if (head) {{ head.rotation.y += gestureTarget.lookAround * held; head.rotation.x += Math.sin(eased * Math.PI) * 0.025; }}
          if (neck)   neck.rotation.y += gestureTarget.lookAround * 0.22 * held;
          break;
        case 'sideGlance':
          if (head) {{ head.rotation.y += gestureTarget.sideGlance * held; head.rotation.z -= gestureTarget.sideGlance * 0.18 * intensity; }}
          safeSetExpression('relaxed', 0.28);
          break;
        case 'meetGaze':
          if (head) {{ head.rotation.y *= 1 - held * 0.78; head.rotation.z *= 1 - held * 0.70; head.rotation.x += held * 0.018; }}
          if (neck) {{ neck.rotation.y *= 1 - held * 0.55; neck.rotation.z *= 1 - held * 0.55; }}
          safeSetExpression('relaxed', 0.30);
          safeSetExpression('happy', 0.04 * held);
          break;
        case 'curiousTilt':
          if (head) {{ head.rotation.z += gestureTarget.curiousTilt * held; head.rotation.x -= 0.018 * intensity; }}
          if (neck)   neck.rotation.z += gestureTarget.curiousTilt * 0.45 * held;
          break;
        case 'shiftWeight':
          if (hips)  hips.position.x  += Math.sin(eased * Math.PI) * 0.016;
          if (spine) spine.rotation.z += Math.sin(eased * Math.PI) * 0.018;
          if (head)  head.rotation.z  -= Math.sin(eased * Math.PI) * 0.012;
          break;
        case 'hairTuck':
          if (gestureTarget.hairSide < 0) {{
            if (lUA) {{ lUA.rotation.z = REST.leftUpperArm.z + intensity * 0.34; lUA.rotation.x = REST.leftUpperArm.x - intensity * 0.12; }}
            if (lLA) {{ lLA.rotation.x = REST.leftLowerArm.x - intensity * 0.26; lLA.rotation.z = REST.leftLowerArm.z - intensity * 0.10; }}
            if (lH)  {{ lH.rotation.y  = REST.leftHand.y + intensity * 0.16; lH.rotation.z = REST.leftHand.z - intensity * 0.10; }}
          }} else {{
            if (rUA) {{ rUA.rotation.z = REST.rightUpperArm.z - intensity * 0.34; rUA.rotation.x = REST.rightUpperArm.x - intensity * 0.12; }}
            if (rLA) {{ rLA.rotation.x = REST.rightLowerArm.x - intensity * 0.26; rLA.rotation.z = REST.rightLowerArm.z + intensity * 0.10; }}
            if (rH)  {{ rH.rotation.y  = REST.rightHand.y - intensity * 0.16; rH.rotation.z = REST.rightHand.z + intensity * 0.10; }}
          }}
          if (head) {{ head.rotation.z -= gestureTarget.hairSide * intensity * 0.035; head.rotation.y += gestureTarget.hairSide * intensity * 0.025; }}
          break;
        case 'stretchNeck':
          if (neck) neck.rotation.x += -intensity * 0.05;
          if (head) head.rotation.x += -intensity * 0.04;
          break;
      }}
      if (progress >= 1) gestureState = 'none';
    }}

    function applyBlink(dt) {{
      if (!vrm?.expressionManager) return;
      if (blinkPhase === 'wait') {{
        blinkTimer -= dt;
        if (blinkTimer <= 0) {{ blinkPhase = 'closing'; blinkT = 0; }}
      }} else if (blinkPhase === 'closing') {{
        blinkT += dt;
        safeSetExpression('blink', Math.min(blinkT / BLINK_CLOSE_DUR, 1));
        if (blinkT >= BLINK_CLOSE_DUR) {{ blinkPhase = 'opening'; blinkT = 0; }}
      }} else if (blinkPhase === 'opening') {{
        blinkT += dt;
        safeSetExpression('blink', 1 - Math.min(blinkT / BLINK_OPEN_DUR, 1));
        if (blinkT >= BLINK_OPEN_DUR) {{
          blinkPhase = 'wait'; blinkTimer = nextBlinkWait();
          safeSetExpression('blink', 0);
        }}
      }}
    }}

    let lastAudio      = null;
    let audioContext   = null;
    let analyserAudio  = null;
    let audioData      = null;
    let audioSource    = null;
    let audioMeterOk   = false;
    let meteredAudio   = null;

    function setupAudioMeter(audio) {{
      if (!audio || (audioMeterOk && audio === meteredAudio)) return;
      try {{
        audioContext = audioContext || new (window.AudioContext || window.webkitAudioContext)();
        if (audioContext.state === 'suspended') audioContext.resume().catch(() => {{}});
        analyserAudio = audioContext.createAnalyser();
        analyserAudio.fftSize = 512;
        analyserAudio.smoothingTimeConstant = 0.72;
        audioData   = new Uint8Array(analyserAudio.fftSize);
        audioSource = audio._aikoMediaSource || audioContext.createMediaElementSource(audio);
        audio._aikoMediaSource = audioSource;
        audioSource.connect(analyserAudio);
        analyserAudio.connect(audioContext.destination);
        audioMeterOk = true;
        meteredAudio = audio;
      }} catch (err) {{
        console.warn('[aiko-vrm] audio meter unavailable; using text lip-sync fallback', err);
        audioMeterOk = false;
        meteredAudio = null;
        analyserAudio = null;
        audioData = null;
      }}
    }}

    function getAudioMouth() {{
      if (!analyserAudio || !audioData) return null;
      analyserAudio.getByteTimeDomainData(audioData);
      let sum = 0;
      for (let i = 0; i < audioData.length; i++) {{
        const centered = (audioData[i] - 128) / 128;
        sum += centered * centered;
      }}
      const rms    = Math.sqrt(sum / audioData.length);
      const gated  = Math.max(0, rms - 0.018);
      const target = Math.min(1, Math.pow(gated * 7.5, 0.72));
      smoothedAudioMouth += (target - smoothedAudioMouth) * (target > smoothedAudioMouth ? 0.55 : 0.28);
      return smoothedAudioMouth;
    }}

    function findParentAudio() {{
      try {{ return parent.document.querySelector('#aiko-audio audio') || parent.document.querySelector('audio'); }}
      catch (_) {{ return null; }}
    }}

    function syncAudioState(audio) {{
      if (!audio) return;
      setSpeaking(!audio.paused && !audio.ended && audio.currentTime >= 0);
    }}

    function attachAudio(audio) {{
      if (!audio) return;
      if (audio !== lastAudio) {{
        lastAudio = audio;

        audio.addEventListener('play', () => {{
          setSpeaking(true);
          setupAudioMeter(audio);
          // ttsText is pushed via postMessage from the parent page's JS bridge;
          // _aikoLatestTtsText is set on window by that same bridge as a fallback.
          if (window._aikoLatestTtsText) {{
            setSpeechText(window._aikoLatestTtsText, audio.duration);
            window._aikoLatestTtsText = '';
          }}
        }});

        audio.addEventListener('playing', () => {{
          setSpeaking(true);
          setupAudioMeter(audio);
          if (window._aikoLatestTtsText) {{
            setSpeechText(window._aikoLatestTtsText, audio.duration);
            window._aikoLatestTtsText = '';
          }}
        }});

        audio.addEventListener('timeupdate', () => {{
          if (!audio.paused && audio.currentTime > 0) setSpeaking(true);
        }});
        audio.addEventListener('pause',  () => setSpeaking(false));
        audio.addEventListener('ended',  () => setSpeaking(false));
      }}
      syncAudioState(audio);
    }}

    setInterval(() => attachAudio(findParentAudio()), 500);

    // ── postMessage API ───────────────────────────────────────────────────────
    // Receives messages from app.py's tts_text.change JS bridge (and anything
    // else that wants to control the avatar).
    window.addEventListener('message', (e) => {{
      try {{
        const msg = (typeof e.data === 'string') ? JSON.parse(e.data) : e.data;

        // Expression / emotion
        if (msg.expression !== undefined) {{
          setExpression(msg.expression, msg.intensity ?? 1.0);
          clearTimeout(exprResetTimer);
          if (msg.expression && msg.expression !== 'neutral') {{
            exprResetTimer = setTimeout(() => setExpression('relaxed', 0.25), EXPR_RESET_DELAY);
          }}
        }}

        // Speech text for lip-sync + caption (sent by the JS bridge alongside audio)
        const incomingText = msg.ttsText ?? msg.speechText ?? msg.text;
        if (incomingText !== undefined) {{
          // Store for the audio 'play' event to pick up if it fires after postMessage
          window._aikoLatestTtsText = incomingText;
          setSpeechText(incomingText, msg.duration ?? msg.audioDuration ?? null);
          if (msg.speaking === undefined && msg.playNow) setSpeaking(true);
        }}

        // Direct speaking state override
        if (msg.speaking !== undefined) setSpeaking(msg.speaking);

        // Direct viseme override (for external controllers)
        if (msg.viseme !== undefined) {{
          setMouth(msg.weight ?? 1.0, msg.viseme);
          clearTimeout(window._aikoMouthTimer);
          window._aikoMouthTimer = setTimeout(clearMouth, 180);
        }}

      }} catch (_) {{}}
    }});

    // ── VRM loader ────────────────────────────────────────────────────────────
    const loader = new GLTFLoader();
    loader.register(parser => new VRMLoaderPlugin(parser));

    function loadVrm(index = 0) {{
      const url = VRM_URLS[index];
      if (!url) {{
        document.getElementById('load-msg').textContent = 'VRM load failed';
        return;
      }}
      document.getElementById('load-msg').textContent = `loading VRM (${{index + 1}}/${{VRM_URLS.length}})…`;
      loader.load(url, gltf => {{
        vrm = gltf.userData.vrm;
        window._aikoVrm = vrm;
        VRMUtils.removeUnnecessaryVertices(vrm.scene);
        vrm.scene.traverse(o => {{ if (o.frustumCulled) o.frustumCulled = false; }});
        vrm.scene.rotation.y = 0;
        scene.add(vrm.scene);

        setTimeout(() => {{
          const lUA = vrm.humanoid?.getRawBoneNode('leftUpperArm');
          const rUA = vrm.humanoid?.getRawBoneNode('rightUpperArm');
          console.log('[aiko-vrm] leftUpperArm rotation:', lUA?.rotation);
          console.log('[aiko-vrm] rightUpperArm rotation:', rUA?.rotation);
        }}, 500);

        setExpression('relaxed', 0.25);
        console.log('Available expressions:', expressionNames());
        document.getElementById('loader').classList.add('fade');
        setTimeout(() => document.getElementById('loader').remove(), 550);
      }}, undefined, err => {{
        console.warn('[aiko-vrm] candidate failed', url, err);
        loadVrm(index + 1);
      }});
    }}

    loadVrm();

    // ── Render loop ───────────────────────────────────────────────────────────
    function tick() {{
      requestAnimationFrame(tick);
      resize();
      const dt = Math.min(clock.getDelta(), 0.05);
      controls.update();
      if (vrm) vrm.update(dt);
      applyIdle(dt);
      applyGestures(dt);

      const now        = performance.now();
      const textMouth  = speaking ? currentTextMouth(now) : null;
      const audioMouth = speaking ? getAudioMouth()       : null;

      if (audioMouth !== null) {{
        setMouth(audioMouth, textMouth?.viseme ?? 'aa');
      }} else if (textMouth) {{
        setMouth(textMouth.weight, textMouth.viseme);
      }} else if (speaking) {{
        mouth = 0.12 + Math.abs(Math.sin(now / 110)) * 0.65;
        setMouth(mouth, 'aa');
      }} else {{
        smoothedAudioMouth = 0;
        clearMouth();
      }}

      applyBlink(dt);
      renderer.render(scene, camera);
    }}
    tick();
  </script>
</body>
</html>"""

    return (
        '<iframe id="aiko-vrm-frame" title="Aiko VRM Avatar" '
        'sandbox="allow-scripts allow-same-origin" '
        f'srcdoc="{html.escape(srcdoc, quote=True)}"></iframe>'
    )