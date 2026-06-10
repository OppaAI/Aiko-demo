"""HTML helpers for embedding the Aiko VRM avatar in Gradio."""
from __future__ import annotations

import html
import os
from pathlib import Path
from urllib.parse import quote


def resolve_vrm_path() -> Path:
    """Return the configured VRM path, preferring the bundled Aiko model."""
    candidates = [
        Path(os.getenv("AIKO_VRM_PATH", "assets/Aiko.vrm")),
        Path("static/Aiko.vrm"),
        Path("assets/Original.vrm"),
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
    """Return an iframe containing the Three/VRM viewer and lip-sync bridge."""
    if isinstance(vrm_urls, str):
        vrm_urls = [vrm_urls]

    srcdoc = rf"""<!DOCTYPE html>
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
      background: radial-gradient(circle at 36% 18%, #21183f 0, #090711 48%, #050509 100%);
      color: #c8b8e8;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
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
      padding: 24px 30px 72px;
      background: linear-gradient(180deg, rgba(5,5,10,.48), transparent 20%, transparent 78%, rgba(5,5,10,.42));
    }}
    #top {{ display: flex; justify-content: space-between; align-items: center; gap: 12px; }}
    #status {{ display: flex; align-items: center; gap: 8px; color: #8b7ab6; font-size: 11px; }}
    #dot {{ width: 8px; height: 8px; border-radius: 999px; background: #5c46a0; box-shadow: 0 0 10px rgba(155,127,212,.35); }}
    #dot.speaking {{ background: #d68cff; box-shadow: 0 0 16px rgba(214,140,255,.9); animation: pulse .6s infinite; }}
    #emotion {{ letter-spacing: .22em; text-transform: uppercase; font-size: 11px; color: #9a86cf; }}
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
      <div id="emotion">relaxed</div>
      <div id="status"><span id="dot"></span><span id="status-text">idle</span></div>
    </div>
  </div>
  <div id="loader"><h1>🌸 Aiko</h1><p id="load-msg">loading VRM…</p></div>

  <script type="module">
    import * as THREE from 'three';
    import {{ OrbitControls }} from 'three/addons/controls/OrbitControls.js';
    import {{ GLTFLoader }} from 'three/addons/loaders/GLTFLoader.js';
    import {{ VRMLoaderPlugin, VRMUtils }} from '@pixiv/three-vrm';

    const RAW_VRM_URLS = {vrm_urls!r};
    const VISEME_PRESETS = ['aa', 'ih', 'ou', 'ee', 'oh'];
    const TEXT_VISEME_MAP = {{
      a: 'aa', á: 'aa', à: 'aa', â: 'aa', ä: 'aa', あ: 'aa', ア: 'aa',
      i: 'ih', í: 'ih', ì: 'ih', î: 'ih', ï: 'ih', y: 'ih', い: 'ih', イ: 'ih',
      u: 'ou', ú: 'ou', ù: 'ou', û: 'ou', ü: 'ou', う: 'ou', ウ: 'ou',
      e: 'ee', é: 'ee', è: 'ee', ê: 'ee', ë: 'ee', え: 'ee', エ: 'ee',
      o: 'oh', ó: 'oh', ò: 'oh', ô: 'oh', ö: 'oh', お: 'oh', オ: 'oh', ん: 'oh', ン: 'oh',
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
          if (/^https?:\/\//.test(raw)) urls.push(raw);
          else {{
            urls.push(new URL(raw, parentOrigin).href);
            urls.push(new URL(raw.replace(/^\//, ''), withTrailingSlash(parentHref)).href);
          }}
        }} catch (err) {{ console.warn('[aiko-vrm] bad VRM URL', raw, err); }}
      }}
      return [...new Set(urls)];
    }}

    const VRM_URLS = buildVrmUrls(RAW_VRM_URLS);
    const canvas = document.getElementById('canvas');
    const renderer = new THREE.WebGLRenderer({{ canvas, antialias: true, alpha: true }});
    renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    renderer.outputColorSpace = THREE.SRGBColorSpace;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(22, 1, 0.1, 100);
    camera.position.set(-0.16, 1.16, 2.05);

    const controls = new OrbitControls(camera, canvas);
    controls.target.set(-0.22, 1.13, 0);
    controls.enableDamping = true;
    controls.enablePan = false;
    controls.minDistance = 1.0;
    controls.maxDistance = 3.2;

    scene.add(new THREE.HemisphereLight(0xded4ff, 0x21182f, 2.4));
    const key = new THREE.DirectionalLight(0xffffff, 2.7);
    key.position.set(1.8, 3.0, 2.5);
    scene.add(key);
    const rim = new THREE.DirectionalLight(0x9b7cff, 1.5);
    rim.position.set(-2.5, 1.4, -1.2);
    scene.add(rim);

    let vrm = null;
    let speaking = false;
    const clock = new THREE.Clock();
    let idleTime = 0;
    let blinkTimer = 3.0 + Math.random() * 4.0;
    let blinkPhase = 'wait';
    let blinkT = 0;
    const BLINK_CLOSE_DUR = 0.07;
    const BLINK_OPEN_DUR = 0.10;
    let speechText = '';
    let speechVisemes = [];
    let speechStartedAt = 0;
    let speechDuration = 1;
    let lastAudio = null;

    const dot = document.getElementById('dot');
    const statusText = document.getElementById('status-text');
    const emotionEl = document.getElementById('emotion');

    function resize() {{
      const w = Math.max(1, canvas.clientWidth);
      const h = Math.max(1, canvas.clientHeight);
      renderer.setSize(w, h, false);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
    }}
    addEventListener('resize', resize);

    function expressionNames() {{
      return (vrm?.expressionManager?.expressions ?? []).map(e => e.expressionName ?? e.name).filter(Boolean);
    }}
    function hasExpression(name) {{ return expressionNames().includes(name); }}
    function safeSetExpression(name, weight) {{ try {{ vrm?.expressionManager?.setValue(name, weight); }} catch (_) {{}} }}
    function setExpression(name, weight = 1) {{
      if (!vrm?.expressionManager) return;
      for (const k of ['happy', 'relaxed', 'angry', 'sad', 'surprised']) safeSetExpression(k, k === name ? weight : 0);
      emotionEl.textContent = name || 'neutral';
    }}
    function setMouth(weight, viseme = 'aa') {{
      if (!vrm) return;
      const clamped = Math.max(0, Math.min(1, Number(weight) || 0));
      let usedExpression = false;
      if (vrm.expressionManager) {{
        for (const k of VISEME_PRESETS) {{
          if (hasExpression(k)) {{
            vrm.expressionManager.setValue(k, k === viseme ? clamped : 0);
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
      setExpression(speaking ? 'happy' : 'relaxed', speaking ? 0.55 : 0.25);
      if (!speaking) clearMouth();
    }}
    function textToVisemes(text) {{
      const tokens = [];
      let lastViseme = 'aa';
      for (const rawChar of String(text || '').toLowerCase()) {{
        const viseme = TEXT_VISEME_MAP[rawChar];
        if (viseme) {{ lastViseme = viseme; tokens.push({{ viseme, weight: 0.88 }}); }}
        else if (/[,.;:!?。！？、\s]/.test(rawChar)) tokens.push({{ viseme: lastViseme, weight: 0.08 }});
        else if (/[bcdfghjklmnpqrstvwxz]/.test(rawChar)) tokens.push({{ viseme: lastViseme, weight: 0.28 }});
      }}
      return tokens.length ? tokens : [{{ viseme: 'aa', weight: 0.25 }}];
    }}
    function setSpeechText(text, duration = null) {{
      const nextText = String(text || '').trim();
      if (!nextText) return;
      speechText = nextText;
      speechVisemes = textToVisemes(speechText);
      speechDuration = Number(duration) > 0 ? Number(duration) : Math.max(1, Math.min(14, speechText.length * 0.07));
      speechStartedAt = performance.now();
    }}
    function currentTextMouth(now) {{
      if (!speechVisemes.length) return null;
      const duration = lastAudio && Number.isFinite(lastAudio.duration) && lastAudio.duration > 0 ? lastAudio.duration : speechDuration;
      const elapsed = lastAudio && !lastAudio.paused ? lastAudio.currentTime : (now - speechStartedAt) / 1000;
      const progress = Math.max(0, Math.min(0.999, elapsed / Math.max(0.25, duration)));
      const index = Math.min(speechVisemes.length - 1, Math.floor(progress * speechVisemes.length));
      const token = speechVisemes[index];
      const syllablePhase = Math.sin(progress * speechVisemes.length * Math.PI);
      return {{ viseme: token.viseme, weight: Math.max(0, Math.min(1, token.weight * (0.55 + Math.abs(syllablePhase) * 0.45))) }};
    }}
    function findParentAudio() {{ try {{ return parent.document.querySelector('#aiko-audio audio') || parent.document.querySelector('audio'); }} catch (_) {{ return null; }} }}
    function attachAudio(audio) {{
      if (!audio) return;
      if (audio !== lastAudio) {{
        lastAudio = audio;
        audio.addEventListener('play', () => setSpeaking(true));
        audio.addEventListener('playing', () => setSpeaking(true));
        audio.addEventListener('timeupdate', () => {{ if (!audio.paused && audio.currentTime > 0) setSpeaking(true); }});
        audio.addEventListener('pause', () => setSpeaking(false));
        audio.addEventListener('ended', () => setSpeaking(false));
      }}
      setSpeaking(!audio.paused && !audio.ended && audio.currentTime >= 0);
    }}
    setInterval(() => attachAudio(findParentAudio()), 500);

    window.addEventListener('message', (e) => {{
      try {{
        const msg = typeof e.data === 'string' ? JSON.parse(e.data) : e.data;
        if (msg.speaking !== undefined) setSpeaking(msg.speaking);
        if (msg.expression !== undefined) setExpression(msg.expression, msg.intensity ?? 1.0);
        const incomingText = msg.ttsText ?? msg.speechText ?? msg.text;
        if (incomingText !== undefined) setSpeechText(incomingText, msg.duration ?? msg.audioDuration ?? null);
        if (msg.viseme !== undefined) {{
          setMouth(msg.weight ?? 1.0, msg.viseme);
          clearTimeout(window._aikoMouthTimer);
          window._aikoMouthTimer = setTimeout(clearMouth, 180);
        }}
      }} catch (_) {{}}
    }});

    function getBone(name) {{
      const h = vrm?.humanoid;
      if (!h) return null;
      return h.getRawBoneNode?.(name) || h.getNormalizedBoneNode?.(name) || null;
    }}
    function applyIdle(dt) {{
      if (!vrm?.humanoid) return;
      idleTime += dt;
      const chest = getBone('chest');
      const spine = getBone('spine');
      const head = getBone('head');
      const hips = getBone('hips');
      const breath = Math.sin(idleTime * 0.83) * 0.013;
      if (chest) chest.rotation.x = breath;
      if (spine) spine.rotation.x = breath * 0.5;
      if (hips) {{ hips.rotation.z = Math.sin(idleTime * 0.41) * 0.012; hips.position.x = Math.sin(idleTime * 0.41) * 0.003; }}
      if (head) {{
        head.rotation.y = Math.sin(idleTime * 0.31) * 0.055 + Math.sin(idleTime * 1.13) * 0.012;
        head.rotation.z = Math.sin(idleTime * 0.27 + 1.1) * 0.018;
        head.rotation.x = Math.sin(idleTime * 0.53) * 0.012;
      }}
      if (!speaking) safeSetExpression('relaxed', 0.20 + Math.sin(idleTime * 0.37) * 0.035);
    }}
    function applyBlink(dt) {{
      if (!vrm?.expressionManager) return;
      if (blinkPhase === 'wait') {{ blinkTimer -= dt; if (blinkTimer <= 0) {{ blinkPhase = 'closing'; blinkT = 0; }} }}
      else if (blinkPhase === 'closing') {{ blinkT += dt; safeSetExpression('blink', Math.min(blinkT / BLINK_CLOSE_DUR, 1)); if (blinkT >= BLINK_CLOSE_DUR) {{ blinkPhase = 'opening'; blinkT = 0; }} }}
      else if (blinkPhase === 'opening') {{ blinkT += dt; safeSetExpression('blink', 1 - Math.min(blinkT / BLINK_OPEN_DUR, 1)); if (blinkT >= BLINK_OPEN_DUR) {{ blinkPhase = 'wait'; blinkTimer = 3.0 + Math.random() * 4.0; safeSetExpression('blink', 0); }} }}
    }}

    const loader = new GLTFLoader();
    loader.register(parser => new VRMLoaderPlugin(parser));
    function loadVrm(index = 0) {{
      const url = VRM_URLS[index];
      if (!url) {{ document.getElementById('load-msg').textContent = 'VRM load failed'; return; }}
      document.getElementById('load-msg').textContent = `loading VRM (${{index + 1}}/${{VRM_URLS.length}})…`;
      loader.load(url, gltf => {{
        vrm = gltf.userData.vrm;
        window._aikoVrm = vrm;
        VRMUtils.removeUnnecessaryVertices(vrm.scene);
        vrm.scene.traverse(o => {{ if (o.frustumCulled) o.frustumCulled = false; }});
        vrm.scene.rotation.y = 0;
        scene.add(vrm.scene);
        setExpression('relaxed', 0.25);
        document.getElementById('loader').classList.add('fade');
        setTimeout(() => document.getElementById('loader').remove(), 550);
      }}, undefined, err => {{ console.warn('[aiko-vrm] candidate failed', url, err); loadVrm(index + 1); }});
    }}
    loadVrm();

    function tick() {{
      requestAnimationFrame(tick);
      resize();
      const dt = Math.min(clock.getDelta(), 0.05);
      controls.update();
      if (vrm) vrm.update(dt);
      applyIdle(dt);
      const now = performance.now();
      const textMouth = speaking ? currentTextMouth(now) : null;
      if (textMouth) setMouth(textMouth.weight, textMouth.viseme);
      else if (speaking) setMouth(0.12 + Math.abs(Math.sin(now / 110)) * 0.65, 'aa');
      else clearMouth();
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