# ui/vrm_viewer.py
VRM_VIEWER = """
<div id="aiko-vrm-root" style="
    width:100%; height:100%; min-height:600px; position:relative;
    background: rgba(10,8,20,0.4); border-radius:20px;
    overflow:hidden; border:1px solid rgba(155,127,212,0.22);
    box-shadow: inset 0 0 40px rgba(91,47,168,0.1), 0 8px 32px rgba(0,0,0,0.3);">

  <canvas id="aiko-canvas" style="width:100%;height:100%;display:block;outline:none;"></canvas>

  <!-- Glassmorphic status overlay -->
  <div id="aiko-vrm-status" style="
      position:absolute; bottom:16px; left:50%; transform:translateX(-50%);
      padding:6px 16px; text-align:center;
      font-family:'SF Mono', 'Courier New', monospace; font-size:10px; letter-spacing:1.5px;
      color:rgba(196,168,255,0.85);
      background:rgba(15,10,30,0.6); backdrop-filter:blur(12px) saturate(1.2);
      border:1px solid rgba(155,127,212,0.2); border-radius:20px;
      box-shadow:0 4px 12px rgba(0,0,0,0.2); transition:all 0.3s ease;
      max-width:90%; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">
    ✨ initializing…
  </div>

  <!-- Loading spinner -->
  <div id="aiko-vrm-loader" style="
      position:absolute; top:50%; left:50%; transform:translate(-50%,-50%);
      display:flex; flex-direction:column; align-items:center; gap:12px;
      pointer-events:none; transition:opacity 0.5s ease;">
    <div style="
        width:40px; height:40px; border:2px solid rgba(155,127,212,0.2);
        border-top-color:rgba(196,168,255,0.9); border-radius:50%;
        animation:spin 1s linear infinite;"></div>
    <span style="font-size:11px; color:rgba(155,127,212,0.7); letter-spacing:2px;">LOADING</span>
  </div>

<style>
@keyframes spin { to { transform: rotate(360deg); } }
@keyframes pulse { 0%,100% { opacity:0.6; } 50% { opacity:1; } }
#aiko-vrm-root:focus-within { border-color: rgba(155,127,212,0.4); }
</style>

<script type="module">
// ── imports ───────────────────────────────────────────────────────────────────
import * as THREE from 'https://unpkg.com/three@0.168.0/build/three.module.js';
import { GLTFLoader } from 'https://unpkg.com/three@0.168.0/examples/jsm/loaders/GLTFLoader.js';
import { VRMLoaderPlugin, VRMUtils } from 'https://unpkg.com/@pixiv/three-vrm@3/lib/three-vrm.module.js';
import { OrbitControls } from 'https://unpkg.com/three@0.168.0/examples/jsm/controls/OrbitControls.js';

// ── DOM refs ──────────────────────────────────────────────────────────────────
const root      = document.getElementById('aiko-vrm-root');
const canvas    = document.getElementById('aiko-canvas');
const statusEl  = document.getElementById('aiko-vrm-status');
const loaderEl  = document.getElementById('aiko-vrm-loader');

const log = msg => {
    statusEl.textContent = msg;
    statusEl.style.animation = 'pulse 2s ease-in-out';
    console.log('[aiko-vrm]', msg);
};

// ── HEAD probe ────────────────────────────────────────────────────────────────
async function probeVRM() {
    const candidates = [
        '/file=static/Aiko.vrm',
        '/file=static/aiko.vrm',
        'static/Aiko.vrm',
        './static/Aiko.vrm',
        '/static/Aiko.vrm',
        'Aiko.vrm',
    ];
    for (const path of candidates) {
        try {
            log(`🔍 probing ${path}`);
            const r = await fetch(path, { method: 'HEAD', mode: 'no-cors' });
            // no-cors means we can't read status, but if no error, likely exists
            log(`✓ found → ${path}`);
            return path;
        } catch (e) {
            log(`✗ ${path}`);
        }
    }
    // Fallback: just try the first one anyway
    return candidates[0];
}

// ── renderer ──────────────────────────────────────────────────────────────────
const W = () => root.clientWidth  || 400;
const H = () => root.clientHeight || 600;

const renderer = new THREE.WebGLRenderer({ 
    canvas, 
    alpha: true, 
    antialias: true,
    powerPreference: "high-performance"
});
renderer.setSize(W(), H());
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.1;

// ── scene / camera ────────────────────────────────────────────────────────────
const scene  = new THREE.Scene();
// Soft fog for depth
scene.fog = new THREE.FogExp2(0x080612, 0.02);

const camera = new THREE.PerspectiveCamera(30, W() / H(), 0.1, 20);
camera.position.set(0, 1.35, 3.2);

const controls = new OrbitControls(camera, renderer.domElement);
controls.target.set(0, 1.0, 0);
controls.enableDamping = true;
controls.dampingFactor = 0.08;
controls.minDistance = 1.5;
controls.maxDistance = 6;
controls.maxPolarAngle = Math.PI / 1.8; // Don't go below ground
controls.update();

// ── lights ────────────────────────────────────────────────────────────────────
scene.add(new THREE.AmbientLight(0xffffff, 0.5));
const hemi = new THREE.HemisphereLight(0xd0b0ff, 0x080612, 0.6);
scene.add(hemi);

const sun = new THREE.DirectionalLight(0xfff0ff, 1.0);
sun.position.set(2, 4, 3);
scene.add(sun);

const rim = new THREE.DirectionalLight(0xb090ff, 0.5);
rim.position.set(-2, 1.5, -2);
scene.add(rim);

const fill = new THREE.DirectionalLight(0x9070ff, 0.3);
fill.position.set(-1, 0.5, 2);
scene.add(fill);

// ── VRM state ─────────────────────────────────────────────────────────────────
let vrm        = null;
let blinkTimer = 2 + Math.random() * 3;
const clock    = new THREE.Clock();

// ── expression API ────────────────────────────────────────────────────────────
const EXPR_NAMES = ['happy', 'sad', 'surprised', 'relaxed', 'angry', 'blink'];

function setExpr(name, val = 1.0) {
    if (!vrm?.expressionManager) return;
    // Smooth transition would be better, but direct set is fine for now
    EXPR_NAMES.forEach(e => {
        if (e !== name) vrm.expressionManager.setValue(e, 0);
    });
    if (name && name !== 'neutral') vrm.expressionManager.setValue(name, val);
}

// Public API for chat integration
window.aikoSetExpression = (name) => {
    const mapped = name === 'thinking' ? 'relaxed' : name;
    setExpr(mapped);
    // Auto-return to neutral after 4s unless it's a hold state
    if (!['sad', 'angry'].includes(mapped)) {
        setTimeout(() => setExpr('neutral'), 4000);
    }
};

window._aikoExprFromText = (text) => {
    const t = text.toLowerCase();
    let expr = 'neutral';
    if (/!\s|wow|amazing|whoa|holy|omg/.test(t)) expr = 'surprised';
    else if (/sorry|sad|unfortunate|cannot|can't|don't know|error|fail/.test(t)) expr = 'sad';
    else if (/hmm|think|let me|consider|wonder|searching|loading/.test(t)) expr = 'relaxed';
    else if (/haha|lol|♥|❤|love|cute|kawaii|nice|great|thanks/.test(t)) expr = 'happy';
    else if (/angry|mad|stupid|hate|dumb/.test(t)) expr = 'angry';
    
    setExpr(expr);
    if (expr !== 'neutral') {
        setTimeout(() => setExpr('neutral'), 5000);
    }
};

// ── animate ───────────────────────────────────────────────────────────────────
function animate() {
    requestAnimationFrame(animate);
    const delta = clock.getDelta();
    const t     = clock.elapsedTime;

    if (vrm) {
        vrm.update(delta);

        // Idle: gentle head sway
        const head = vrm.humanoid?.getNormalizedBoneNode('head');
        if (head) {
            head.rotation.x = Math.sin(t * 0.50) * 0.03;
            head.rotation.y = Math.sin(t * 0.33) * 0.02;
            head.rotation.z = Math.sin(t * 0.27) * 0.015;
        }

        // Idle: breathing (chest + spine)
        const chest = vrm.humanoid?.getNormalizedBoneNode('chest');
        if (chest) chest.rotation.x = Math.sin(t * 0.8) * 0.012;

        const spine = vrm.humanoid?.getNormalizedBoneNode('spine');
        if (spine) spine.rotation.z = Math.sin(t * 0.4) * 0.005;

        // Auto-blink with randomness
        blinkTimer -= delta;
        if (blinkTimer <= 0) {
            setExpr('blink', 1);
            setTimeout(() => {
                if (vrm?.expressionManager) vrm.expressionManager.setValue('blink', 0);
            }, 100 + Math.random() * 60);
            blinkTimer = 2 + Math.random() * 5;
        }
    }

    controls.update();
    renderer.render(scene, camera);
}
animate();

// ── resize handler ────────────────────────────────────────────────────────────
const resizeObserver = new ResizeObserver(() => {
    const w = W();
    const h = H();
    if (w > 0 && h > 0) {
        renderer.setSize(w, h);
        camera.aspect = w / h;
        camera.updateProjectionMatrix();
    }
});
resizeObserver.observe(root);

// ── visibility check (pause when not visible) ─────────────────────────────────
document.addEventListener('visibilitychange', () => {
    // Could pause animation here to save GPU
});

// ── load VRM ──────────────────────────────────────────────────────────────────
(async () => {
    const vrmPath = await probeVRM();
    
    if (!vrmPath) {
        log('❌ VRM not found — add static/Aiko.vrm');
        loaderEl.style.opacity = '0';
        return;
    }

    const loader = new GLTFLoader();
    loader.register(parser => new VRMLoaderPlugin(parser));

    loader.load(
        vrmPath,
        (gltf) => {
            vrm = gltf.userData.vrm;
            if (!vrm) {
                log('⚠️ loaded GLB but no VRM data');
                return;
            }
            
            VRMUtils.removeUnnecessaryJoints(vrm.scene);
            scene.add(vrm.scene);
            
            // Face camera properly
            vrm.scene.rotation.y = Math.PI;
            
            // Hide loader
            loaderEl.style.opacity = '0';
            setTimeout(() => loaderEl.style.display = 'none', 500);
            
            log('🌸 Aiko-chan ready');
            
            // Initial expression
            setExpr('happy');
            setTimeout(() => setExpr('neutral'), 1500);
        },
        (xhr) => {
            if (xhr.total && xhr.total > 0) {
                const pct = Math.round((xhr.loaded / xhr.total) * 100);
                log(`📦 loading… ${pct}%`);
            } else {
                log(`📦 loading… ${Math.round(xhr.loaded / 1024)} KB`);
            }
        },
        (err) => {
            log(`❌ error: ${err?.message || 'unknown'}`);
            console.error('[aiko-vrm]', err);
            loaderEl.style.opacity = '0';
        }
    );
})();
</script>
</div>
"""