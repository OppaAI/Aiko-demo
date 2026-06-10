"""VRM avatar embed for the Gradio/Hugging Face Space UI."""

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
    """Build Gradio file-serving URL candidates for an allowed local path.

    Gradio 5/6 serves files from /gradio_api/file=<path>, while older builds
    accepted /file=<path>. Returning both lets the browser retry instead of
    showing a silent VRM failure when the Space runtime changes.
    """
    encoded_path = quote(path.as_posix(), safe="/:")
    return [f"/gradio_api/file={encoded_path}", f"/file={encoded_path}"]


def gradio_file_url(path: Path) -> str:
    """Return the preferred Gradio file-serving URL for compatibility callers."""
    return gradio_file_urls(path)[0]


def avatar_html(vrm_urls: str | list[str]) -> str:
    """Return an iframe containing the Three/VRM viewer.

    The iframe keeps module scripts/import maps isolated from Gradio's own DOM,
    then watches the parent gr.Audio element (#aiko-audio) with Web Audio to
    drive lip sync from the actual TTS MP3 playback level.

    The mouth is driven through VRM expression presets first (aa/ih/ou/ee/oh),
    because many VRM avatars do not expose a normalized ``jaw`` bone. A jaw-bone
    rotation is used only as an optional fallback.

    Lip sync uses a layered approach:
      1. Web Audio analyser on the actual MP3 playback (best, but requires the
         audio element to be CORS-clean; if createMediaElementSource throws or
         the analyser stays silent, we fall back).
      2. Text-derived viseme sequence timed against audio.currentTime/duration
         (works regardless of CORS).
      3. Generic sine-wave "talking" mouth motion as a last resort.

    Idle behaviour now also includes a gesture state machine (look around,
    head tilt, weight shift, hand-to-hair, neck stretch) layered on top of the
    base breathing/sway animation, only active while not speaking.

    Expression/viseme/text control is via postMessage (works in HF Spaces):
        parent.frames['aiko-vrm-frame'].postMessage({expression:'happy',intensity:0.8}, '*')
        parent.frames['aiko-vrm-frame'].postMessage({viseme:'A',weight:0.6}, '*')
        parent.frames['aiko-vrm-frame'].postMessage({ttsText:'Hello!',duration:1.2}, '*')
    """
    if isinstance(vrm_urls, str):
        vrm_urls = [vrm_urls]

    srcdoc = f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width,initial-scale=1\" />
  <style>
    * {{ box-sizing: border-box; }}
    html, body {{
      margin: 0;
      width: 100%;
      height: 100%;
      overflow: hidden;
      background: radial-gradient(circle at 50% 12%, #22183f 0, #0b0a14 48%, #050509 100%);
      color: #c8b8e8;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, \"Liberation Mono\", monospace;
    }}
    #wrap {{ position: fixed; inset: 0; }}
    canvas {{ display: block; width: 100% !important; height: 100% !important; }}
    #hud {{
      position: fixed;
      inset: 0;
      pointer-events: none;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      padding: 16px 18px;
      background: linear-gradient(180deg, rgba(5,5,10,.55), transparent 24%, transparent 70%, rgba(5,5,10,.62));
    }}
    #top {{ display: flex; justify-content: space-between; align-items: center; gap: 12px; }}
    #title {{ letter-spacing: .22em; text-transform: uppercase; color: #b39cff; font-size: 12px; }}
    #status {{ display: flex; align-items: center; gap: 8px; color: #8b7ab6; font-size: 11px; }}
    #dot {{ width: 8px; height: 8px; border-radius: 999px; background: #4b3a79; box-shadow: 0 0 10px rgba(155,127,212,.2); }}
    #dot.speaking {{ background: #d68cff; box-shadow: 0 0 16px rgba(214,140,255,.9); animation: pulse .6s infinite; }}
    #bottom {{ display: flex; justify-content: space-between; align-items: end; color: #7867a3; font-size: 11px; }}
    #emotion {{ letter-spacing: .16em; text-transform: uppercase; }}
    #log {{ text-align: right; max-width: 54%; line-height: 1.6; }}
    #loader {{
      position: fixed; inset: 0; display: grid; place-content: center; gap: 18px; text-align: center;
      background: #080810; z-index: 10; transition: opacity .45s ease;
    }}
    #loader.fade {{ opacity: 0; pointer-events: none; }}
    #loader h1 {{ margin: 0; color: #b39cff; letter-spacing: .28em; text-transform: uppercase; font-size: 22px; }}
    #loader p {{ margin: 0; color: #69578f; font-size: 11px; letter-spacing: .16em; }}
    @keyframes pulse {{ 0%,100% {{ opacity: 1 }} 50% {{ opacity: .45 }} }}
  </style>
  <script type=\"importmap\">
  {{
    \"imports\": {{
      \"three\": \"https://cdn.jsdelivr.net/npm/three@0.170.0/build/three.module.js\",
      \"three/addons/\": \"https://cdn.jsdelivr.net/npm/three@0.170.0/examples/jsm/\",
      \"@pixiv/three-vrm\": \"https://cdn.jsdelivr.net/npm/@pixiv/three-vrm@3/lib/three-vrm.module.min.js\"
    }}
  }}
  </script>
</head>
<body>
  <div id=\"wrap\"><canvas id=\"canvas\"></canvas></div>
  <div id=\"hud\">
    <div id=\"top\"><div id=\"title\">Aiko-chan · VRM</div><div id=\"status\"><span id=\"dot\"></span><span id=\"status-text\">idle</span></div></div>
    <div id=\"bottom\"><div id=\"emotion\">neutral</div><div id=\"log\">waiting for Aiko's voice…</div></div>
  </div>
  <div id=\"loader\"><h1>Aiko-chan</h1><p id=\"load-msg\">loading VRM…</p></div>
  <script type=\"module\">
    import * as THREE from 'three';
    import {{ OrbitControls }} from 'three/addons/controls/OrbitControls.js';
    import {{ GLTFLoader }} from 'three/addons/loaders/GLTFLoader.js';
    import {{ VRMLoaderPlugin, VRMUtils }} from '@pixiv/three-vrm';

    const RAW_VRM_URLS = {vrm_urls!r};
    const VISEME_MAP = {{ A: 'aa', I: 'ih', U: 'ou', E: 'ee', O: 'oh' }};
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
      let parentHref = null;
      let parentOrigin = null;
      try {{
        parentHref = parent.location.href;
        parentOrigin = parent.location.origin;
        }} catch (_) {{
        parentHref = window.location.href;
        parentOrigin = window.location.origin;
      }}
      for (const raw of rawUrls) {{
        if (!raw) continue;
        try {{
          if (/^https?:\/\//.test(raw)) {{
            urls.push(raw);
          }} else {{
            urls.push(new URL(raw, parentOrigin).href);
            urls.push(new URL(raw.replace(/^\//, ''), withTrailingSlash(parentHref)).href);
          }}
        }} catch (err) {{
          console.warn('[aiko-vrm] bad VRM URL candidate', raw, err);
        }}
      }}
      return [...new Set(urls)];
    }}

    const VRM_URLS = buildVrmUrls(RAW_VRM_URLS);
    const canvas = document.getElementById('canvas');
    const renderer = new THREE.WebGLRenderer({{ canvas, antialias: true, alpha: true }});
    renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    renderer.outputColorSpace = THREE.SRGBColorSpace;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(28, 1, 0.1, 100);
    camera.position.set(0, 1.35, 3.0);

    const controls = new OrbitControls(camera, canvas);
    controls.target.set(0, 1.28, 0);
    controls.enableDamping = true;
    controls.enablePan = false;
    controls.minDistance = 1.4;
    controls.maxDistance = 4.2;

    scene.add(new THREE.HemisphereLight(0xded4ff, 0x21182f, 2.4));
    const key = new THREE.DirectionalLight(0xffffff, 2.7);
    key.position.set(1.8, 3.0, 2.5);
    scene.add(key);
    const rim = new THREE.DirectionalLight(0x9b7cff, 1.5);
    rim.position.set(-2.5, 1.4, -1.2);
    scene.add(rim);
    scene.add(new THREE.GridHelper(10, 20, 0x1a0a2a, 0x100820));

    let vrm = null;
    let mouth = 0;
    let smoothedAudioMouth = 0;
    let speaking = false;
    const clock = new THREE.Clock();
    let blinkTimer = 3.0 + Math.random() * 4.0;
    let blinkPhase = 'wait';
    let blinkT = 0;
    const BLINK_CLOSE_DUR = 0.07;
    const BLINK_OPEN_DUR = 0.10;
    let exprResetTimer = null;
    const EXPR_RESET_DELAY = 4000;

    // --- Idle procedural animation ---
    // A relaxed arms-down baseline plus tiny sine offsets, so Aiko breathes and
    // weight-shifts without the outward arm arch from the previous parade-rest pose.
    let idleTime = 0;
    let speechText = '';
    let speechVisemes = [];
    let speechStartedAt = 0;
    let speechDuration = 0;
    const REST = window._REST = {{
      leftUpperArm: {{ x: 0.02, y: 0.0, z: -1.28 }},
      rightUpperArm: {{ x: 0.02, y: 0.0, z: 1.28 }},
      leftLowerArm: {{ x: -0.12, y: 0.0, z: -0.08 }},
      rightLowerArm: {{ x: -0.12, y: 0.0, z: 0.08 }},
      leftHand: {{ x: 0.0, y: 0.08, z: 0.0 }},
      rightHand: {{ x: 0.0, y: -0.08, z: 0.0 }},
    }};

    const dot = document.getElementById('dot');
    const statusText = document.getElementById('status-text');
    const emotion = document.getElementById('emotion');
    const log = document.getElementById('log');

    function nextBlinkWait() {{ return 3.0 + Math.random() * 4.0; }}
    function expressionNames() {{
      const expressions = vrm?.expressionManager?.expressions ?? [];
      return expressions.map((expr) => expr.expressionName ?? expr.name).filter(Boolean);
    }}
    function hasExpression(name) {{ return expressionNames().includes(name); }}
    function safeSetExpression(name, weight) {{
      try {{ vrm?.expressionManager?.setValue(name, weight); }} catch (_) {{}}
    }}

    function resize() {{
      const w = Math.max(1, canvas.clientWidth);
      const h = Math.max(1, canvas.clientHeight);
      renderer.setSize(w, h, false);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
    }}
    addEventListener('resize', resize);

    function setExpression(name, weight = 1) {{
      if (!vrm?.expressionManager) return;
      for (const key of ['happy', 'relaxed', 'angry', 'sad', 'surprised']) {{
        safeSetExpression(key, key === name ? weight : 0);
      }}
      emotion.textContent = name || 'neutral';
    }}

    function setMouth(weight, viseme = 'aa') {{
      if (!vrm) return;
      const clamped = Math.max(0, Math.min(1, Number(weight) || 0));
      const preset = VISEME_MAP[viseme] ?? viseme ?? 'aa';
      let usedExpression = false;

      if (vrm.expressionManager) {{
        for (const key of VISEME_PRESETS) {{
          if (hasExpression(key)) {{
            safeSetExpression(key, key === preset ? clamped : 0);
            usedExpression = true;
          }}
        }}
        // three-vrm applies expression weights during update(); when we change
        // them after update() in this render loop, force the manager to flush so
        // the mouth movement is visible on the same frame.
        try {{ vrm.expressionManager.update?.(); }} catch (_) {{}}
      }}

      // Fallback only: many VRMs do not expose a normalized jaw bone.
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
      if (!speaking) clearMouth();
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
      // Allow re-arming on identical consecutive lines (Aiko may repeat a
      // short phrase) by always resetting the timer/visemes when called from
      // a fresh 'play'/'playing' event, even if the text string is unchanged.
      speechText = nextText;
      speechVisemes = textToVisemes(speechText);
      speechDuration = estimateSpeechDuration(speechText, duration);
      speechStartedAt = performance.now();
      log.textContent = `text lip sync ready: ${{speechText.slice(0, 42)}}${{speechText.length > 42 ? '…' : ''}}`;
    }}

    function currentTextMouth(now) {{
      if (!speechVisemes.length) return null;
      const audioDuration = lastAudio && Number.isFinite(lastAudio.duration) && lastAudio.duration > 0 ? lastAudio.duration : speechDuration;
      const duration = Math.max(0.25, audioDuration || speechDuration || 1);
      const elapsed = lastAudio && !lastAudio.paused ? lastAudio.currentTime : (now - speechStartedAt) / 1000;
      const progress = Math.max(0, Math.min(0.999, elapsed / duration));
      const index = Math.min(speechVisemes.length - 1, Math.floor(progress * speechVisemes.length));
      const token = speechVisemes[index];
      const syllablePhase = Math.sin(progress * speechVisemes.length * Math.PI);
      return {{
        viseme: token.viseme,
        weight: Math.max(0, Math.min(1, token.weight * (0.55 + Math.abs(syllablePhase) * 0.45))),
      }};
    }}

    function findParentSpeechText() {{
          if (window._aikoLatestTtsText) {{
            const t = window._aikoLatestTtsText;
            window._aikoLatestTtsText = '';
            return t;
          }}
          try {{
            const doc = parent.document;
            const el = doc.querySelector('#aiko-tts-text textarea, #aiko-tts-text input');
            return el ? (el.value || el.textContent || '') : '';
          }} catch (_) {{ return ''; }}
        }}

    function getBone(name) {{
      const humanoid = vrm?.humanoid;
      if (!humanoid) return null;
      return humanoid.getRawBoneNode?.(name) || humanoid.getNormalizedBoneNode?.(name) || null;
    }}

    function applyIdle(dt) {{
      if (!vrm?.humanoid) return;
      idleTime += dt;

      const breath = Math.sin(idleTime * 0.83) * 0.013;
      const chest = getBone('chest');
      const spine = getBone('spine');
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
        safeSetExpression('happy', Math.max(0, Math.sin(idleTime * 0.19 - 0.8)) * 0.035);
      }}

      const neck = getBone('neck');
      if (neck && head) {{
        neck.rotation.y = head.rotation.y * 0.3;
        neck.rotation.z = head.rotation.z * 0.3;
      }}

      const leftUpperArm = getBone('leftUpperArm');
      const rightUpperArm = getBone('rightUpperArm');
      const leftLowerArm = getBone('leftLowerArm');
      const rightLowerArm = getBone('rightLowerArm');
      const leftHand = getBone('leftHand');
      const rightHand = getBone('rightHand');

      if (leftUpperArm) {{
        leftUpperArm.rotation.x = REST.leftUpperArm.x + Math.sin(idleTime * 0.47) * 0.010;
        leftUpperArm.rotation.y = REST.leftUpperArm.y + Math.sin(idleTime * 0.33) * 0.006;
        leftUpperArm.rotation.z = REST.leftUpperArm.z + Math.sin(idleTime * 0.41) * 0.008;
      }}
      if (rightUpperArm) {{
        rightUpperArm.rotation.x = REST.rightUpperArm.x + Math.sin(idleTime * 0.53 + 0.9) * 0.010;
        rightUpperArm.rotation.y = REST.rightUpperArm.y + Math.sin(idleTime * 0.35 + 0.4) * 0.006;
        rightUpperArm.rotation.z = REST.rightUpperArm.z + Math.sin(idleTime * 0.37 + 0.7) * 0.008;
      }}
      if (leftLowerArm) {{
        leftLowerArm.rotation.x = REST.leftLowerArm.x + Math.sin(idleTime * 0.61) * 0.008;
        leftLowerArm.rotation.y = REST.leftLowerArm.y;
        leftLowerArm.rotation.z = REST.leftLowerArm.z + Math.sin(idleTime * 0.43) * 0.004;
      }}
      if (rightLowerArm) {{
        rightLowerArm.rotation.x = REST.rightLowerArm.x + Math.sin(idleTime * 0.57 + 1.4) * 0.008;
        rightLowerArm.rotation.y = REST.rightLowerArm.y;
        rightLowerArm.rotation.z = REST.rightLowerArm.z + Math.sin(idleTime * 0.51 + 0.5) * 0.004;
      }}
      if (leftHand) {{
        leftHand.rotation.x = REST.leftHand.x;
        leftHand.rotation.y = REST.leftHand.y + Math.sin(idleTime * 0.33) * 0.008;
        leftHand.rotation.z = REST.leftHand.z;
      }}
      if (rightHand) {{
        rightHand.rotation.x = REST.rightHand.x;
        rightHand.rotation.y = REST.rightHand.y + Math.sin(idleTime * 0.29 + 1.2) * 0.008;
        rightHand.rotation.z = REST.rightHand.z;
      }}
    }}

    // --- Idle gesture system ---
    // Layered on top of applyIdle(). Periodically picks a small natural
    // "fidget" gesture (look around, tilt head, shift weight, touch hair,
    // stretch neck) and eases it in/out over a few seconds. Suppressed while
    // speaking so it doesn't fight lip-sync head motion.
    let gestureState = 'none';
    let gestureT = 0;
    let gestureDuration = 0;
    let gestureCooldown = 4 + Math.random() * 6;
    let gestureTarget = null;

    const GESTURES = ['lookAround', 'tiltHead', 'shiftWeight', 'touchHair', 'stretchNeck'];

    function pickGesture() {{
      const g = GESTURES[Math.floor(Math.random() * GESTURES.length)];
      gestureState = g;
      gestureT = 0;
      gestureDuration = {{
        lookAround: 2.5,
        tiltHead: 2.0,
        shiftWeight: 3.0,
        touchHair: 3.5,
        stretchNeck: 2.5,
      }}[g];
      gestureTarget = {{
        lookAround: (Math.random() - 0.5) * 0.5,
        tiltHead: (Math.random() - 0.5) * 0.25,
      }};
    }}

    function easeInOutSine(t) {{ return -(Math.cos(Math.PI * t) - 1) / 2; }}

    function applyGestures(dt) {{
      if (!vrm?.humanoid) return;
      if (speaking) {{ gestureState = 'none'; return; }}

      if (gestureState === 'none') {{
        gestureCooldown -= dt;
        if (gestureCooldown <= 0) {{
          pickGesture();
          gestureCooldown = 5 + Math.random() * 8; // next gesture in 5-13s
        }}
        return;
      }}

      gestureT += dt;
      const progress = Math.min(1, gestureT / gestureDuration);
      // bell curve: ramp in, hold, ramp out
      const intensity = Math.sin(progress * Math.PI);
      const eased = easeInOutSine(progress);

      const head = getBone('head');
      const neck = getBone('neck');
      const leftUpperArm = getBone('leftUpperArm');
      const leftLowerArm = getBone('leftLowerArm');
      const leftHand = getBone('leftHand');
      const spine = getBone('spine');
      const hips = getBone('hips');

      switch (gestureState) {{
        case 'lookAround':
          if (head) head.rotation.y += gestureTarget.lookAround * intensity;
          break;

        case 'tiltHead':
          if (head) head.rotation.z += gestureTarget.tiltHead * intensity;
          break;

        case 'shiftWeight':
          if (hips) hips.position.x += Math.sin(eased * Math.PI) * 0.018;
          if (spine) spine.rotation.z += Math.sin(eased * Math.PI) * 0.02;
          break;

        case 'touchHair':
          // Raise left arm toward head, hold briefly, lower again.
          if (leftUpperArm) {{
            leftUpperArm.rotation.z = REST.leftUpperArm.z + intensity * 1.6;
            leftUpperArm.rotation.x = REST.leftUpperArm.x - intensity * 0.6;
          }}
          if (leftLowerArm) {{
            leftLowerArm.rotation.x = REST.leftLowerArm.x - intensity * 1.4;
          }}
          if (leftHand) {{
            leftHand.rotation.z = REST.leftHand.z - intensity * 0.4;
          }}
          if (head) head.rotation.z += intensity * 0.06; // slight head lean into hand
          break;

        case 'stretchNeck':
          if (neck) neck.rotation.x += -intensity * 0.05;
          if (head) head.rotation.x += -intensity * 0.04;
          break;
      }}

      if (progress >= 1) {{
        gestureState = 'none';
      }}
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
          blinkPhase = 'wait';
          blinkTimer = nextBlinkWait();
          safeSetExpression('blink', 0);
        }}
      }}
    }}

    let lastAudio = null;
    let audioContext = null;
    let audioAnalyser = null;
    let audioAnalyserData = null;
    let analyserAudio = null;
    let analyserStartedAt = 0;
    let analyserSilentSince = 0;
    let lastAudioTime = 0;

    function getAudioMouth() {{
      return null;
    }}

    function findParentAudio() {{
      try {{ return parent.document.querySelector('#aiko-audio audio') || parent.document.querySelector('audio'); }} catch (_) {{ return null; }}
    }}

    // NOTE: The Web Audio analyser approach (createMediaElementSource +
    // AnalyserNode) requires the <audio> element to be served with CORS
    // headers (Access-Control-Allow-Origin). Gradio's static file server
    // (allowed_paths / /tmp/aiko_tts) does not send these headers, and
    // setting audio.crossOrigin='anonymous' on such a source either fails to
    // load the file or taints it, sometimes breaking autoplay entirely.
    // We deliberately do NOT use the analyser; lip sync is driven purely by
    // text-derived visemes timed against audio.currentTime/duration (see
    // currentTextMouth / textToVisemes below), which needs no CORS access.
    function syncAudioState(audio) {{
      if (!audio) return;
      setSpeaking(!audio.paused && !audio.ended && audio.currentTime >= 0);
    }}

    function attachAudio(audio) {{
    if (!audio) return;
      if (audio !== lastAudio) {{
        lastAudio = audio;
        log.textContent = 'linked to Gradio MP3 output';

        audio.addEventListener('play', () => {{
          setSpeaking(true);
          let tries = 0;
          const poll = setInterval(() => {{
            const text = findParentSpeechText();
            console.log('[Aiko] poll try', tries, '| text:', JSON.stringify(text));
            if (text) {{
              clearInterval(poll);
              setSpeechText(text, audio.duration);
              log.textContent = 'lip sync: ' + text.slice(0, 40);
            }} else if (++tries >= 10) {{
              clearInterval(poll);
              log.textContent = 'lip sync: no text (fallback sine)';
            }}
          }}, 200);
        }});

        audio.addEventListener('playing', () => {{
          setSpeaking(true);
          const text = findParentSpeechText();
          if (text) setSpeechText(text, audio.duration);
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

    window.addEventListener('message', (e) => {{
      try {{
        const msg = (typeof e.data === 'string') ? JSON.parse(e.data) : e.data;
        if (msg.speaking !== undefined) setSpeaking(msg.speaking);
        if (msg.expression !== undefined) {{
          setExpression(msg.expression, msg.intensity ?? 1.0);
          clearTimeout(exprResetTimer);
          if (msg.expression && msg.expression !== 'neutral') {{
            exprResetTimer = setTimeout(() => setExpression('relaxed', 0.25), EXPR_RESET_DELAY);
          }}
        }}
        const incomingText = msg.ttsText ?? msg.speechText ?? msg.text;
        if (incomingText !== undefined) {{
          window._aikoLatestTtsText = incomingText;
          setSpeechText(incomingText, msg.duration ?? msg.audioDuration ?? null);
          console.log('[Aiko] postMessage text:', incomingText.slice(0, 60));
          if (msg.speaking === undefined && msg.playNow) setSpeaking(true);
        }}
        if (msg.viseme !== undefined) {{
          setMouth(msg.weight ?? 1.0, msg.viseme);
          clearTimeout(window._aikoMouthTimer);
          window._aikoMouthTimer = setTimeout(clearMouth, 180);
        }}
      }} catch (_) {{}}
    }});

    const loader = new GLTFLoader();
    loader.register(parser => new VRMLoaderPlugin(parser));

    function loadVrm(index = 0) {{
      const url = VRM_URLS[index];
      if (!url) {{
        document.getElementById('load-msg').textContent = 'VRM load failed';
        log.textContent = 'No Gradio file URL could load static/Aiko.vrm. Check allowed_paths and browser console.';
        return;
      }}
      document.getElementById('load-msg').textContent = `loading VRM (${{index + 1}}/${{VRM_URLS.length}})…`;
      log.textContent = url;
      loader.load(url, gltf => {{
        vrm = gltf.userData.vrm;
        window._aikoVrm = vrm;
        VRMUtils.removeUnnecessaryVertices(vrm.scene);
        vrm.scene.traverse(o => {{ if (o.frustumCulled) o.frustumCulled = false; }});
        // Aiko.vrm already faces the camera in the standalone aiko.html viewer.
        // Do not rotate by Math.PI here, or HF Spaces starts by showing her back.
        vrm.scene.rotation.y = 0;
        scene.add(vrm.scene);
        setExpression('relaxed', 0.25);
        log.textContent = `loaded: Aiko.vrm; mouth presets: ${{expressionNames().filter(n => VISEME_PRESETS.includes(n)).join(', ') || 'none, using jaw fallback'}}`;
        console.log('Available expressions:', expressionNames());
        document.getElementById('load-msg').textContent = 'ready';
        document.getElementById('loader').classList.add('fade');
        setTimeout(() => document.getElementById('loader').remove(), 550);
      }}, undefined, err => {{
        console.warn('[aiko-vrm] candidate failed', url, err);
        loadVrm(index + 1);
      }});
    }}
    loadVrm();

    function tick() {{
      requestAnimationFrame(tick);
      resize();
      const dt = Math.min(clock.getDelta(), 0.05);
      controls.update();
      if (vrm) vrm.update(dt);
      applyIdle(dt);
      applyGestures(dt);
      const now = performance.now();
      const textMouth = speaking ? currentTextMouth(now) : null;
      const audioMouth = speaking ? getAudioMouth() : null;
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