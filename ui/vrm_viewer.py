# VRM viewer — loads static/Aiko.vrm via Three.js + @pixiv/three-vrm.
# Status bar shows live progress so you always know what's happening.
# Probes multiple path candidates so it works across local / HF Spaces.

VRM_VIEWER = """
<div id="aiko-vrm-root" style="
    width:100%; height:520px; position:relative;
    background:rgba(10,8,20,0.7); border-radius:16px;
    overflow:hidden; border:1px solid rgba(155,127,212,0.18);">

  <canvas id="aiko-canvas" style="width:100%;height:100%;display:block;"></canvas>

  <!-- status bar — always visible, updated throughout load -->
  <div id="aiko-vrm-status" style="
      position:absolute; bottom:0; left:0; right:0;
      padding:4px 10px; text-align:center;
      font-family:'Courier New',monospace; font-size:9px; letter-spacing:2px;
      color:rgba(155,127,212,0.6);
      background:rgba(8,6,18,0.55); backdrop-filter:blur(4px);">
    initializing…
  </div>

<script type="module">
// ── imports ───────────────────────────────────────────────────────────────────
import * as THREE from 'https://unpkg.com/three@0.168.0/build/three.module.js';
import { GLTFLoader }
    from 'https://unpkg.com/three@0.168.0/examples/jsm/loaders/GLTFLoader.js';
import { VRMLoaderPlugin, VRMUtils }
    from 'https://unpkg.com/@pixiv/three-vrm@3/lib/three-vrm.module.js';
import { OrbitControls }
    from 'https://unpkg.com/three@0.168.0/examples/jsm/controls/OrbitControls.js';

// ── helpers ───────────────────────────────────────────────────────────────────
const statusEl = document.getElementById('aiko-vrm-status');
const log = msg => {
    statusEl.textContent = msg;
    console.log('[aiko-vrm]', msg);
};

// HEAD probe — fast, no body download, finds which path actually works
async function probeVRM() {
    const candidates = [
        '/file=static/Aiko.vrm',
        '/file=static/aiko.vrm',
        '/file=Aiko.vrm',
        'static/Aiko.vrm',
        './static/Aiko.vrm',
        '/static/Aiko.vrm',
        'Aiko.vrm',
    ];
    for (const path of candidates) {
        try {
            log(`probing ${path}`);
            const r = await fetch(path, { method: 'HEAD' });
            if (r.ok) { log(`found → ${path}`); return path; }
            log(`${r.status} ${path}`);
        } catch (e) {
            log(`net-err ${path}`);
        }
    }
    return null;
}

// ── renderer ──────────────────────────────────────────────────────────────────
const canvas = document.getElementById('aiko-canvas');
const root   = document.getElementById('aiko-vrm-root');
const W = root.clientWidth  || 400;
const H = root.clientHeight || 520;

const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
renderer.setSize(W, H);
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.outputColorSpace = THREE.SRGBColorSpace;

// ── scene / camera ────────────────────────────────────────────────────────────
const scene  = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(30, W / H, 0.1, 20);
camera.position.set(0, 1.4, 3.5);

const controls = new OrbitControls(camera, renderer.domElement);
controls.target.set(0, 1.0, 0);
controls.enableDamping = true;
controls.dampingFactor = 0.08;
controls.update();

// ── lights ────────────────────────────────────────────────────────────────────
scene.add(new THREE.AmbientLight(0xffffff, 0.65));
const sun = new THREE.DirectionalLight(0xfff0ff, 1.2);
sun.position.set(1, 3, 2);
scene.add(sun);
const rim = new THREE.DirectionalLight(0xd0b0ff, 0.4);
rim.position.set(-2, 1, -1);
scene.add(rim);

// ── VRM state ─────────────────────────────────────────────────────────────────
let vrm        = null;
let blinkTimer = 3 + Math.random() * 3;
const clock    = new THREE.Clock();

// ── expression API ────────────────────────────────────────────────────────────
const EXPR_NAMES = ['happy', 'sad', 'surprised', 'relaxed', 'angry', 'blink'];

function setExpr(name, val = 1.0) {
    if (!vrm?.expressionManager) return;
    EXPR_NAMES.forEach(e => vrm.expressionManager.setValue(e, 0));
    if (name && name !== 'neutral') vrm.expressionManager.setValue(name, val);
}

// public — same interface as SVG fallback
window.aikoSetExpression = name =>
    setExpr(name === 'thinking' ? 'relaxed' : name);

window._aikoExprFromText = text => {
    const t = text.toLowerCase();
    let expr = 'neutral';
    if (/!\s|wow|amazing|whoa/.test(t))                               expr = 'surprised';
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
    const t     = clock.elapsedTime;

    if (vrm) {
        vrm.update(delta);   // spring-bone physics runs here

        // idle: gentle head sway
        const head = vrm.humanoid?.getNormalizedBoneNode('head');
        if (head) {
            head.rotation.x = Math.sin(t * 0.50) * 0.04;
            head.rotation.z = Math.sin(t * 0.31) * 0.025;
        }

        // idle: breathing (chest)
        const chest = vrm.humanoid?.getNormalizedBoneNode('chest');
        if (chest) chest.rotation.x = Math.sin(t * 0.8) * 0.015;

        // auto-blink
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

// ── resize ────────────────────────────────────────────────────────────────────
new ResizeObserver(() => {
    const w = root.clientWidth;
    const h = root.clientHeight;
    renderer.setSize(w, h);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
}).observe(root);

// ── load VRM ──────────────────────────────────────────────────────────────────
const vrmPath = await probeVRM();

if (!vrmPath) {
    log('VRM not found — add static/Aiko.vrm + allowed_paths=["static"]');
} else {
    const loader = new GLTFLoader();
    loader.register(parser => new VRMLoaderPlugin(parser));

    loader.load(
        vrmPath,
        gltf => {
            vrm = gltf.userData.vrm;
            if (!vrm) {
                log('loaded GLB but no VRM data — check file is VRM 1.0');
                return;
            }
            VRMUtils.removeUnnecessaryJoints(vrm.scene);
            scene.add(vrm.scene);
            vrm.scene.rotation.y = Math.PI;   // face camera
            log('aiko-chan ✓');
        },
        xhr => {
            if (xhr.total) {
                const pct = Math.round(xhr.loaded / xhr.total * 100);
                const kb  = Math.round(xhr.loaded / 1024);
                const tot = Math.round(xhr.total  / 1024);
                log(`loading… ${pct}%  (${kb} / ${tot} KB)`);
            } else {
                log(`loading… ${Math.round(xhr.loaded / 1024)} KB`);
            }
        },
        err => {
            log(`error: ${err?.message || err}`);
            console.error('[aiko-vrm]', err);
        }
    );
}
</script>
</div>
"""