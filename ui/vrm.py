"""VRM avatar embed for the Gradio/Hugging Face Space UI."""

from __future__ import annotations

import html
import json
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
    then watches the parent gr.Audio element (#aiko-audio when present, or any
    nested audio element) and drives lip sync from the text that produced the
    TTS MP3. This avoids Web Audio analyser/CORS failures in Hugging Face Spaces
    and Gradio's local file server.

    The mouth is driven through VRM expression presets first (aa/ih/ou/ee/oh),
    because many VRM avatars do not expose a normalized ``jaw`` bone. A jaw-bone
    rotation is used only as an optional fallback.

    Lip sync uses a layered approach:
      1. Text-derived viseme sequence timed against audio.currentTime/duration
         (works regardless of CORS).
      2. Generic sine-wave "talking" mouth motion as a last resort if the audio
         starts before text arrives.

    Expression/viseme/text control is via postMessage (works in HF Spaces):
        parent.frames['aiko-vrm-frame'].postMessage({expression:'happy',intensity:0.8}, '*')
        parent.frames['aiko-vrm-frame'].postMessage({viseme:'A',weight:0.6}, '*')
        parent.frames['aiko-vrm-frame'].postMessage({ttsText:'Hello!',duration:1.2}, '*')
    """
    if isinstance(vrm_urls, str):
        vrm_urls = [vrm_urls]

    vrm_urls_json = json.dumps(vrm_urls)
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

    const RAW_VRM_URLS = {vrm_urls_json};
    const VISEME_MAP = {{ A: 'aa', I: 'ih', U: 'ou', E: 'ee', O: 'oh', a: 'aa', i: 'ih', u: 'ou', e: 'ee', o: 'oh', aa: 'aa', ih: 'ih', ou: 'ou', ee: 'ee', oh: 'oh' }};
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
          if ((raw.startsWith('http://') || raw.startsWith('https://'))) {{
            urls.push(raw);
          }} else {{
            urls.push(new URL(raw, parentOrigin).href);
            urls.push(new URL(raw.replace(/^\\//, ''), withTrailingSlash(parentHref)).href);
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
    let speaking = false;
    const clock = new THREE.Clock();
    let blinkTimer = 3.0 + Math.random() * 4.0;
    let blinkPhase = 'wait';
    let blinkT = 0;
    const BLINK_CLOSE_DUR = 0.07;
    const BLINK_OPEN_DUR = 0.10;
    let exprResetTimer = null;
    const EXPR_RESET_DELAY = 4000;

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
      const manager = vrm?.expressionManager;
      if (!manager) return [];
      const fromExpressions = (manager.expressions ?? [])
        .map((expr) => expr.expressionName ?? expr.name)
        .filter(Boolean);
      const fromMap = Object.keys(manager.expressionMap ?? manager._expressionMap ?? {{}});
      return [...new Set([...fromExpressions, ...fromMap])];
    }}
    function hasExpression(name) {{
      const manager = vrm?.expressionManager;
      if (!manager) return false;
      if (typeof manager.getExpression === 'function' && manager.getExpression(name)) return true;
      return expressionNames().includes(name);
    }}
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
      const preset = VISEME_MAP[viseme] ?? String(viseme || 'aa').toLowerCase();
      let usedExpression = false;

      if (vrm.expressionManager) {{
        for (const key of VISEME_PRESETS) {{
          if (hasExpression(key)) {{
            vrm.expressionManager.setValue(key, key === preset ? clamped : 0);
            usedExpression = true;
          }}
        }}
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
      // Do not enable a smile/talk expression while speaking. In VRM1, many
      // non-mouth expressions declare overrideMouth and can suppress aa/ih/ou/ee/oh,
      // which made the startup mouth test work but real lip sync stay still.
      setExpression(speaking ? 'neutral' : 'relaxed', speaking ? 0 : 0.25);
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
        }} else if (/[,.;:!?。！？、\\s]/.test(rawChar)) {{
          tokens.push({{ viseme: lastViseme, weight: 0.08 }});
        }} else if (/[bcdfghjklmnpqrstvwxz]/.test(rawChar)) {{
          tokens.push({{ viseme: lastViseme, weight: 0.28 }});
        }}
      }}
      return tokens.length ? tokens : [{{ viseme: 'aa', weight: 0.25 }}];
    }}

    function setSpeechText(text, duration = null) {{
      const nextText = String(text || '').trim();
      if (!nextText) return false;
      speechText = nextText;
      speechVisemes = textToVisemes(speechText);
      speechDuration = estimateSpeechDuration(speechText, duration);
      speechStartedAt = performance.now();
      log.textContent = `text lip sync ready: ${{speechText.slice(0, 42)}}${{speechText.length > 42 ? '…' : ''}}`;
      return true;
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

    function deepQueryAll(root, selector, out = []) {{
      if (!root) return out;
      try {{
        if (root.querySelectorAll) out.push(...root.querySelectorAll(selector));
        const nodes = root.querySelectorAll ? root.querySelectorAll('*') : [];
        for (const node of nodes) {{
          if (node.shadowRoot) deepQueryAll(node.shadowRoot, selector, out);
        }}
      }} catch (_) {{}}
      return out;
    }}

    function valueFromElement(el) {{
      if (!el) return '';
      const raw = el.value ?? el.textContent ?? el.getAttribute?.('value') ?? '';
      return String(raw || '').trim();
    }}

    function findParentSpeechText() {{
      if (window._aikoLatestTtsText) {{
        const t = String(window._aikoLatestTtsText);
        window._aikoLatestTtsText = '';
        return t;
      }}
      try {{
        if (parent.window._aikoLatestTtsText) return String(parent.window._aikoLatestTtsText);
        if (parent.window._aikoLastTtsText) return String(parent.window._aikoLastTtsText);
      }} catch (_) {{}}
      try {{
        const doc = parent.document;
        const selectors = [
          '[data-aiko-tts-text]',
          '#aiko-tts-text textarea',
          '#aiko-tts-text input',
          '#aiko-tts-text',
          '[id*=\"aiko-tts-text\"] textarea',
          '[id*=\"aiko-tts-text\"] input',
          '[id*=\"aiko-tts-text\"]',
        ];
        for (const selector of selectors) {{
          for (const el of deepQueryAll(doc, selector)) {{
            const text = valueFromElement(el);
            if (text) return text;
          }}
        }}
      }} catch (_) {{}}
      return '';
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

      // Leave arm/hand bones in the VRM author's authored rest pose. VRM1 models
      // can have very different local arm axes; forcing hard-coded upper-arm
      // rotations is what made Aiko snap into a T-pose on the Space.
    }}

    let gestureState = 'none';
    let gestureT = 0;
    let gestureDuration = 0;
    let gestureCooldown = 4 + Math.random() * 6;
    let gestureTarget = null;

    const GESTURES = ['lookAround', 'tiltHead', 'shiftWeight', 'stretchNeck'];

    function pickGesture() {{
      const g = GESTURES[Math.floor(Math.random() * GESTURES.length)];
      gestureState = g;
      gestureT = 0;
      gestureDuration = {{
        lookAround: 2.5,
        tiltHead: 2.0,
        shiftWeight: 3.0,
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
          gestureCooldown = 5 + Math.random() * 8;
        }}
        return;
      }}

      gestureT += dt;
      const progress = Math.min(1, gestureT / gestureDuration);
      const intensity = Math.sin(progress * Math.PI);
      const eased = easeInOutSine(progress);

      const head = getBone('head');
      const neck = getBone('neck');
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
          blinkPhase = 'wait';
          blinkTimer = nextBlinkWait();
          safeSetExpression('blink', 0);
        }}
      }}
    }}

    let lastAudio = null;
    const attachedAudios = new WeakSet();

    function findParentAudios() {{
      try {{
        const doc = parent.document;
        const preferred = deepQueryAll(doc, '#aiko-audio audio');
        const all = deepQueryAll(doc, 'audio');
        return [...new Set([...preferred, ...all])];
      }} catch (_) {{ return []; }}
    }}

    function syncAudioState(audio) {{
      if (!audio) return;
      setSpeaking(!audio.paused && !audio.ended && audio.readyState > 0);
    }}

    function prepareLipSync(audio, reason = 'audio') {{
      lastAudio = audio || lastAudio;
      setSpeaking(true);
      const immediateText = findParentSpeechText();
      if (setSpeechText(immediateText, audio?.duration)) {{
        log.textContent = `lip sync (${{reason}}): ${{immediateText.slice(0, 40)}}`;
        return;
      }}

      let tries = 0;
      clearInterval(window._aikoTextPoll);
      window._aikoTextPoll = setInterval(() => {{
        const text = findParentSpeechText();
        if (setSpeechText(text, audio?.duration)) {{
          clearInterval(window._aikoTextPoll);
          log.textContent = `lip sync: ${{text.slice(0, 40)}}`;
        }} else if (++tries >= 20) {{
          clearInterval(window._aikoTextPoll);
          speechVisemes = [];
          log.textContent = 'lip sync: no text found; using fallback mouth motion';
        }}
      }}, 150);
    }}

    function attachAudio(audio) {{
      if (!audio) return;
      if (!attachedAudios.has(audio)) {{
        attachedAudios.add(audio);
        log.textContent = 'linked to Gradio MP3 output';
        audio.addEventListener('play', () => prepareLipSync(audio, 'play'));
        audio.addEventListener('playing', () => prepareLipSync(audio, 'playing'));
        audio.addEventListener('loadedmetadata', () => {{
          if (!audio.paused && speechText) speechDuration = estimateSpeechDuration(speechText, audio.duration);
        }});
        audio.addEventListener('timeupdate', () => {{
          if (!audio.paused && audio.currentTime > 0) {{
            lastAudio = audio;
            setSpeaking(true);
          }}
        }});
        audio.addEventListener('pause', () => setSpeaking(false));
        audio.addEventListener('ended', () => setSpeaking(false));
      }}
      lastAudio = audio;
      syncAudioState(audio);
    }}

    function attachAvailableAudios() {{
      const audios = findParentAudios();
      for (const audio of audios) attachAudio(audio);
      const playing = audios.find((audio) => !audio.paused && !audio.ended);
      if (playing) lastAudio = playing;
    }}

    setInterval(attachAvailableAudios, 500);
    try {{
      const mo = new MutationObserver(attachAvailableAudios);
      mo.observe(parent.document.documentElement, {{ childList: true, subtree: true }});
    }} catch (_) {{}}

    window.addEventListener('message', (e) => {{
      try {{
        const msg = (typeof e.data === 'string') ? JSON.parse(e.data) : e.data;
        if (!msg || typeof msg !== 'object') return;
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
        VRMUtils.rotateVRM0(vrm);
        vrm.scene.traverse(o => {{ if (o.frustumCulled) o.frustumCulled = false; }});
        scene.add(vrm.scene);
        setExpression('relaxed', 0.25);
        log.textContent = `loaded: Aiko.vrm; mouth presets: ${{expressionNames().filter(n => VISEME_PRESETS.includes(n)).join(', ') || 'none, using jaw fallback'}}`;
        document.getElementById('load-msg').textContent = 'ready';
        document.getElementById('loader').classList.add('fade');
        setTimeout(() => document.getElementById('loader').remove(), 550);
    }}, undefined, err => {{
        console.warn('[aiko-vrm] candidate failed', url, err);
        loadVrm(index + 1);
    }});
    loadVrm();

    function tick() {{
      requestAnimationFrame(tick);
      resize();
      const dt = Math.min(clock.getDelta(), 0.05);
      controls.update();
      applyIdle(dt);
      applyGestures(dt);
      applyBlink(dt);
      if (vrm) vrm.update(dt);

      const now = performance.now();
      const textMouth = speaking ? currentTextMouth(now) : null;
      if (textMouth) {{
        setMouth(textMouth.weight, textMouth.viseme);
      }} else if (speaking) {{
        mouth = 0.12 + Math.abs(Math.sin(now / 110)) * 0.65;
        setMouth(mouth, 'aa');
      }} else {{
        clearMouth();
      }}

      renderer.render(scene, camera);
    }}
    tick();
  </script>
</body>
</html>"""
    return (
        '<iframe id="aiko-vrm-frame" name="aiko-vrm-frame" '
        'title="Aiko VRM Avatar" sandbox="allow-scripts allow-same-origin" '
        f'srcdoc="{html.escape(srcdoc, quote=True)}"></iframe>'
    )

if __name__ == "__main__":
    from pathlib import Path
    p = resolve_vrm_path()
    urls = gradio_file_urls(p)
    result = avatar_html(urls)
    print(f"OK, length={len(result)}")
    # Dump the srcdoc content to a file so you can inspect it
    import re
    m = re.search(r'srcdoc="(.*)"', result, re.DOTALL)
    if m:
        import html
        Path("/tmp/srcdoc_dump.html").write_text(html.unescape(m.group(1)))
        print("Dumped to /tmp/srcdoc_dump.html")