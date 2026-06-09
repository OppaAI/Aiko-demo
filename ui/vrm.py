"""VRM avatar embed for the Gradio/Hugging Face Space UI."""

from __future__ import annotations

import html
import os
from pathlib import Path


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


def gradio_file_url(path: Path) -> str:
    """Build a Gradio file-serving URL for an allowed local path."""
    return f"/file={path.as_posix()}"


def avatar_html(vrm_url: str) -> str:
    """Return an iframe containing the Three/VRM viewer.

    The iframe keeps module scripts/import maps isolated from Gradio's own DOM,
    then watches the parent gr.Audio element (#aiko-audio) to drive simple
    amplitude-based lip sync while Edge TTS MP3 playback is active.
    """
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

    const VRM_URL = {vrm_url!r};
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

    let vrm = null;
    let mouth = 0;
    let speaking = false;
    let lastAudio = null;
    let analyser = null;
    let freq = null;
    let audioContext = null;
    const clock = new THREE.Clock();

    const dot = document.getElementById('dot');
    const statusText = document.getElementById('status-text');
    const emotion = document.getElementById('emotion');
    const log = document.getElementById('log');

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
      audio.addEventListener('pause', () => setSpeaking(false));
      audio.addEventListener('ended', () => setSpeaking(false));
    }}

    setInterval(() => attachAudio(findParentAudio()), 700);

    const loader = new GLTFLoader();
    loader.register(parser => new VRMLoaderPlugin(parser));
    loader.load(VRM_URL, gltf => {{
      vrm = gltf.userData.vrm;
      VRMUtils.removeUnnecessaryVertices(vrm.scene);
      vrm.scene.traverse(o => {{ if (o.frustumCulled) o.frustumCulled = false; }});
      vrm.scene.rotation.y = Math.PI;
      scene.add(vrm.scene);
      setExpression('relaxed', 0.25);
      document.getElementById('load-msg').textContent = 'ready';
      document.getElementById('loader').classList.add('fade');
      setTimeout(() => document.getElementById('loader').remove(), 550);
    }}, undefined, err => {{
      document.getElementById('load-msg').textContent = 'VRM load failed';
      log.textContent = String(err?.message || err);
      console.error('[aiko-vrm] load failed', err);
    }});

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