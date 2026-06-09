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
    accepted /file=<path>.  Returning both lets the browser retry instead of
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
    then watches the parent gr.Audio element (#aiko-audio) to drive simple
    amplitude-based lip sync while Edge TTS MP3 playback is active.

    Expression/viseme control is via postMessage (works in HF Spaces):
        parent.frames['aiko-vrm-frame'].postMessage({expression:'happy',intensity:0.8}, '*')
        parent.frames['aiko-vrm-frame'].postMessage({viseme:'A',weight:0.6}, '*')
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

    function withTrailingSlash(url) {{
      return url.endsWith('/') ? url : url + '/';
    }}

    function buildVrmUrls(rawUrls) {{
      const urls = [];
      let parentHref = null;
      let parentOrigin = null;
      try {{
        parentHref = parent.location.href;
        parentOrigin = parent.location.origin;
      }} catch {{
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

    // Lighting
    scene.add(new THREE.HemisphereLight(0xded4ff, 0x21182f, 2.4));
    const key = new THREE.DirectionalLight(0xffffff, 2.7);
    key.position.set(1.8, 3.0, 2.5);
    scene.add(key);
    const rim = new THREE.DirectionalLight(0x9b7cff, 1.5);
    rim.position.set(-2.5, 1.4, -1.2);
    scene.add(rim);

    // Grid (from standalone viewer)
    scene.add(new THREE.GridHelper(10, 20, 0x1a0a2a, 0x100820));

    let vrm = null;
    let mouth = 0;
    let speaking = false;
    let lastAudio = null;
    let analyser = null;
    let freq = null;
    let audioContext = null;
    const clock = new THREE.Clock();

    let idleTime = 0;
    let blinkTimer = 3.0 + Math.random() * 4.0;
    let blinkPhase = 'wait';
    let blinkT = 0;
    const BLINK_CLOSE_DUR = 0.07;
    const BLINK_OPEN_DUR = 0.10;
    const REST = {{
      leftUpperArm: {{ x: -1.1, z: -0.6 }},
      rightUpperArm: {{ x: -1.1, z: 0.6 }},
      leftLowerArm: {{ x: -0.5, z: -0.4 }},
      rightLowerArm: {{ x: -0.5, z: 0.4 }},
      leftHand: {{ y: 0.4 }},
      rightHand: {{ y: -0.4 }},
    }};

    // Expression state for postMessage control
    const exprTargets = {{}};
    const exprCurrent = {{}};
    const EXPR_LERP = 6;
    let exprResetTimer = null;
    const EXPR_RESET_DELAY = 4000;
    const VISEME_MAP = {{ A: 'aa', I: 'ih', U: 'ou', E: 'ee', O: 'oh' }};

    function nextBlinkWait() {{
      return 3.0 + Math.random() * 4.0;
    }}

    function rawBone(name) {{
      try {{ return vrm?.humanoid?.getRawBoneNode(name) || null; }} catch {{ return null; }}
    }}

    function applyIdle(dt) {{
      if (!vrm?.humanoid) return;
      idleTime += dt;

      const chest = rawBone('chest');
      const spine = rawBone('spine');
      const breath = Math.sin(idleTime * 0.83) * 0.013;
      if (chest) chest.rotation.x = breath;
      if (spine) spine.rotation.x = breath * 0.5;

      const hips = rawBone('hips');
      if (hips) {{
        hips.rotation.z = Math.sin(idleTime * 0.41) * 0.012;
        hips.rotation.x = Math.sin(idleTime * 0.67) * 0.008;
        hips.position.x = Math.sin(idleTime * 0.41) * 0.003;
      }}

      const head = rawBone('head');
      if (head) {{
        head.rotation.y = Math.sin(idleTime * 0.31) * 0.055 + Math.sin(idleTime * 1.13) * 0.012;
        head.rotation.z = Math.sin(idleTime * 0.27 + 1.1) * 0.018 + Math.sin(idleTime * 0.71) * 0.006;
        head.rotation.x = Math.sin(idleTime * 0.53) * 0.012;
      }}

      const neck = rawBone('neck');
      if (neck && head) {{
        neck.rotation.y = head.rotation.y * 0.3;
        neck.rotation.z = head.rotation.z * 0.3;
      }}

      const lUA = rawBone('leftUpperArm');
      const rUA = rawBone('rightUpperArm');
      const lLA = rawBone('leftLowerArm');
      const rLA = rawBone('rightLowerArm');
      const lH  = rawBone('leftHand');
      const rH  = rawBone('rightHand');
      if (lUA) {{ lUA.rotation.x = REST.leftUpperArm.x  + Math.sin(idleTime * 0.47) * 0.012; lUA.rotation.z = REST.leftUpperArm.z  + Math.sin(idleTime * 0.41) * 0.008; }}
      if (rUA) {{ rUA.rotation.x = REST.rightUpperArm.x + Math.sin(idleTime * 0.53 + 0.9) * 0.012; rUA.rotation.z = REST.rightUpperArm.z + Math.sin(idleTime * 0.37 + 0.7) * 0.008; }}
      if (lLA) {{ lLA.rotation.x = REST.leftLowerArm.x  + Math.sin(idleTime * 0.61) * 0.010; lLA.rotation.z = REST.leftLowerArm.z  + Math.sin(idleTime * 0.43) * 0.006; }}
      if (rLA) {{ rLA.rotation.x = REST.rightLowerArm.x + Math.sin(idleTime * 0.57 + 1.4) * 0.010; rLA.rotation.z = REST.rightLowerArm.z + Math.sin(idleTime * 0.51 + 0.5) * 0.006; }}
      if (lH) lH.rotation.y = REST.leftHand.y  + Math.sin(idleTime * 0.33) * 0.008;
      if (rH) rH.rotation.y = REST.rightHand.y + Math.sin(idleTime * 0.29 + 1.2) * 0.008;
    }}

    function applyBlink(dt) {{
      if (!vrm?.expressionManager) return;
      const em = vrm.expressionManager;
      if (blinkPhase === 'wait') {{
        blinkTimer -= dt;
        if (blinkTimer <= 0) {{ blinkPhase = 'closing'; blinkT = 0; }}
      }} else if (blinkPhase === 'closing') {{
        blinkT += dt;
        try {{ em.setValue('blink', Math.min(blinkT / BLINK_CLOSE_DUR, 1)); }} catch {{}}
        if (blinkT >= BLINK_CLOSE_DUR) {{ blinkPhase = 'opening'; blinkT = 0; }}
      }} else if (blinkPhase === 'opening') {{
        blinkT += dt;
        try {{ em.setValue('blink', 1 - Math.min(blinkT / BLINK_OPEN_DUR, 1)); }} catch {{}}
        if (blinkT >= BLINK_OPEN_DUR) {{
          blinkPhase = 'wait';
          blinkTimer = nextBlinkWait();
          try {{ em.setValue('blink', 0); }} catch {{}}
        }}
      }}
    }}

    const dot        = document.getElementById('dot');
    const statusText = document.getElementById('status-text');
    const emotion    = document.getElementById('emotion');
    const log        = document.getElementById('log');

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
      const em = vrm.expressionManager;
      for (const key of ['happy', 'relaxed', 'angry', 'sad', 'surprised']) {{
        try {{ em.setValue(key, key === name ? weight : 0); }} catch {{}}
      }}
      emotion.textContent = name || 'neutral';
    }}

    function setMouth(weight) {{
      if (!vrm?.expressionManager) return;
      for (const key of ['aa', 'ih', 'ou', 'ee', 'oh']) {{
        try {{ vrm.expressionManager.setValue(key, key === 'aa' ? weight : 0); }} catch {{}}
      }}
    }}

    function setSpeaking(active) {{
      speaking = active;
      dot.className = active ? 'speaking' : '';
      statusText.textContent = active ? 'speaking' : 'idle';
      setExpression(active ? 'happy' : 'relaxed', active ? 0.55 : 0.25);
      if (!active) setMouth(0);
    }}

    function findParentAudio() {{
      try {{ return parent.document.querySelector('#aiko-audio audio'); }} catch {{ return null; }}
    }}

    function attachAudio(audio) {{
      if (!audio || audio === lastAudio) return;
      lastAudio = audio;
      log.textContent = 'linked to Gradio MP3 output';
      audio.addEventListener('play', async () => {{
        try {{
          audioContext ||= new AudioContext();
          if (audioContext.state === 'suspended') await audioContext.resume();
          if (!analyser) {{
            analyser = audioContext.createAnalyser();
            analyser.fftSize = 512;
            freq = new Uint8Array(analyser.frequencyBinCount);
            const source = audioContext.createMediaElementSource(audio);
            source.connect(analyser);
            analyser.connect(audioContext.destination);
          }}
        }} catch (err) {{
          log.textContent = 'audio analyser unavailable; using fallback lip sync';
          console.warn('[aiko-vrm] analyser unavailable', err);
        }}
        setSpeaking(true);
      }});
      audio.addEventListener('pause',  () => setSpeaking(false));
      audio.addEventListener('ended',  () => setSpeaking(false));
    }}

    setInterval(() => attachAudio(findParentAudio()), 700);

    // postMessage API — works across iframe boundary in HF Spaces
    // Usage from parent page:
    //   iframe.contentWindow.postMessage({{expression:'happy', intensity:0.8}}, '*')
    //   iframe.contentWindow.postMessage({{viseme:'A', weight:0.6}}, '*')
    window.addEventListener('message', (e) => {{
      try {{
        const msg = (typeof e.data === 'string') ? JSON.parse(e.data) : e.data;
        if (msg.expression !== undefined) {{
          setExpression(msg.expression, msg.intensity ?? 1.0);
          emotion.textContent = msg.expression || 'neutral';
          clearTimeout(exprResetTimer);
          if (msg.expression && msg.expression !== 'neutral') {{
            exprResetTimer = setTimeout(() => setExpression('relaxed', 0.25), EXPR_RESET_DELAY);
          }}
        }}
        if (msg.viseme !== undefined) {{
          const v = VISEME_MAP[msg.viseme] ?? msg.viseme;
          if (vrm?.expressionManager) {{
            for (const k of ['aa','ih','ou','ee','oh']) {{
              try {{ vrm.expressionManager.setValue(k, k === v ? (msg.weight ?? 1.0) : 0); }} catch {{}}
            }}
          }}
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
        VRMUtils.removeUnnecessaryVertices(vrm.scene);
        vrm.scene.traverse(o => {{ if (o.frustumCulled) o.frustumCulled = false; }});
        vrm.scene.rotation.y = Math.PI;
        scene.add(vrm.scene);
        setExpression('relaxed', 0.25);
        document.getElementById('load-msg').textContent = 'ready';
        log.textContent = 'loaded: Aiko.vrm';
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
      const dt = clock.getDelta();
      controls.update();

      if (speaking) {{
        if (analyser && freq) {{
          analyser.getByteFrequencyData(freq);
          let sum = 0;
          for (let i = 4; i < Math.min(freq.length, 80); i++) sum += freq[i];
          mouth = THREE.MathUtils.lerp(mouth, Math.min(1, (sum / 76) / 86), 0.38);
        }} else {{
          mouth = 0.15 + Math.abs(Math.sin(performance.now() / 95)) * 0.7;
        }}
      }} else {{
        mouth = THREE.MathUtils.lerp(mouth, 0, 0.22);
      }}
      setMouth(mouth);

      applyIdle(dt);
      applyBlink(dt);
      if (vrm) vrm.update(dt);
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