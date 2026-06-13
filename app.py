from __future__ import annotations

from pathlib import Path
from dotenv import load_dotenv
import gradio as gr
import time
import inspect
import threading
import re

load_dotenv()

print("GRADIO VERSION:", gr.__version__)
print(inspect.signature(gr.Chatbot))

from core.wakeup import AikoWakeup
from ui.css import AIKO_CSS
from ui.vrm import avatar_html, gradio_file_urls, resolve_vrm_path
from ui.listen import transcribe_file
from ui.speak import speak_to_file


# ─────────────────────────────────────────────
# BOOT
# ─────────────────────────────────────────────
result = AikoWakeup().boot(
    on_loading=lambda k: print(f"[boot] loading: {k}"),
    on_done=lambda k: print(f"[boot] done: {k}"),
    on_skip=lambda k: print(f"[boot] skip: {k}"),
)

think = result.think

if hasattr(think, "join_warmup"):
    think.join_warmup()


VRM_PATH = resolve_vrm_path()
VRM_URLS = gradio_file_urls(VRM_PATH)


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def _strip_for_speech(text: str) -> str:
    text = re.sub(r"\n?🔍 Searching: \*.*?\*\n?", "", text)
    text = re.sub(r"\n?🔧 .*?\n?", "", text)
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    return text.strip()


_SENTENCE_END = re.compile(r'(?<=[.!?。！？\n])\s*')


def _split_ready_sentences(buffer: str):
    parts = _SENTENCE_END.split(buffer)
    if len(parts) <= 1:
        return [], buffer
    *complete, remainder = parts
    return [p for p in complete if p.strip()], remainder


# ─────────────────────────────────────────────
# STREAM CORE
# ─────────────────────────────────────────────
def _stream_response(message: str, history: list, user_id: str = "OppaAI"):
    history = list(history) + [
        {"role": "user", "content": message},
        {"role": "assistant", "content": "▋"},
    ]

    yield history, None

    buffer = ""
    full_text = ""
    last_emitted = ""

    done = threading.Event()
    error = {}

    def _cb(token):
        nonlocal buffer, full_text

        if token.startswith("__SEARCHING__:"):
            q = token.split(":", 1)[1]
            note = f"\n🔍 Searching: *{q}*\n"
            buffer += note
            full_text += note
        elif token.startswith("__TOOL__:"):
            note = token.split(":", 1)[1]
            display = f"\n🔧 {note}\n"
            buffer += display
            full_text += display
        else:
            buffer += token
            full_text += token

    def _run():
        try:
            think.chat(message, user_id=user_id, token_callback=_cb)
        except Exception as e:
            error["e"] = e
        finally:
            done.set()

    threading.Thread(target=_run, daemon=True).start()

    while not done.is_set() or full_text != last_emitted:

        if full_text != last_emitted:
            history[-1]["content"] = full_text + ("▋" if not done.is_set() else "")
            last_emitted = full_text
            yield history, None

        sentences, buffer = _split_ready_sentences(buffer)

        for s in sentences:
            clean = _strip_for_speech(s)
            if not clean:
                continue

            audio_path, emotion = speak_to_file(clean)
            audio_b64 = _encode_audio_b64(audio_path)
            payload = f"AUDIO:{audio_b64}|EMOTION:{emotion}|TEXT:{clean}"
            yield history, payload

        time.sleep(0.03)

    if buffer.strip():
        clean = _strip_for_speech(buffer)
        if clean:
            audio_path, emotion = speak_to_file(clean)
            audio_b64 = _encode_audio_b64(audio_path)
            payload = f"AUDIO:{audio_b64}|EMOTION:{emotion}|TEXT:{clean}"
            yield history, payload

    if error:
        raise error["e"]

    history[-1]["content"] = full_text
    yield history, None


def _encode_audio_b64(audio_path: str | None) -> str:
    if not audio_path:
        return ""
    try:
        import base64
        with open(audio_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception:
        return ""


# ─────────────────────────────────────────────
# WRAPPERS
# ─────────────────────────────────────────────
def _submit(message, history, profile: gr.OAuthProfile | None = None):
    history = history or []
    message = (message or "").strip()
    user_id = profile.username if profile else "guest"

    if not message:
        yield history, None, message
        return

    first = True
    for h, tts in _stream_response(message, history, user_id):
        if first:
            yield h, tts, ""
            first = False
        else:
            yield h, tts, gr.update()


def voice_chat(audio_path, history, profile: gr.OAuthProfile | None = None):
    history = history or []
    user_id = profile.username if profile else "guest"

    if not audio_path:
        return history, None

    transcript = transcribe_file(audio_path)

    if not transcript:
        return history, None

    for h, tts in _stream_response(transcript, history, user_id):
        if h and len(h) >= 2:
            h[-2]["content"] = f"🎙️ {transcript}"
        yield h, tts


# ─────────────────────────────────────────────
# AUTH GATE
# ─────────────────────────────────────────────
def _check_auth(profile: gr.OAuthProfile | None = None):
    logged_in = profile is not None
    print(f"[auth] profile={profile!r} logged_in={logged_in}")
    return (
        gr.update(visible=not logged_in),
        gr.update(visible=logged_in),
    )


# ─────────────────────────────────────────────
# INLINE SCRIPTS (injected via gr.HTML — bypasses HF Space CSP on js= kwargs)
# ─────────────────────────────────────────────
BOOT_SCRIPTS_HTML = """
<script>
(function() {
  // ── Audio player queue ──────────────────────────────────────────────
  function initAudioPlayer() {
    var audio = document.getElementById('_aiko_audio_player');
    if (!audio) {
      audio = document.createElement('audio');
      audio.id = '_aiko_audio_player';
      audio.style.cssText = 'position:absolute;width:0;height:0;opacity:0;pointer-events:none;';
      document.body.appendChild(audio);
    }

    var queue = [];
    var playing = false;

    function playNext() {
      if (!queue.length) { playing = false; return; }
      playing = true;
      var item = queue.shift();
      if (!item.b64) { playNext(); return; }

      var label = document.getElementById('aiko-emotion-label');
      if (label && item.emotion) label.textContent = item.emotion;

      var ttsBox = document.querySelector('#aiko-tts-text textarea');
      if (ttsBox) {
        ttsBox.value = item.text;
        ttsBox.dispatchEvent(new Event('input', { bubbles: true }));
      }

      audio.src = 'data:audio/mpeg;base64,' + item.b64;
      audio.onended = playNext;
      audio.onerror = playNext;
      audio.play().catch(function() {
        document.addEventListener('click', function() { audio.play(); }, { once: true });
      });
    }

    var observer = new MutationObserver(function() {
      var box = document.querySelector('#aiko-tts-text textarea');
      if (!box || !box.value) return;
      var raw = box.value;
      box.value = '';
      if (!raw.startsWith('AUDIO:')) return;
      var m = raw.match(/^AUDIO:(.*?)\|EMOTION:(.*?)\|TEXT:([\s\S]*)$/);
      if (!m) return;
      queue.push({ b64: m[1], emotion: m[2], text: m[3] });
      if (!playing) playNext();
    });

    function attachObserver() {
      var c = document.querySelector('#aiko-tts-text');
      if (c) {
        observer.observe(c, { subtree: true, characterData: true, childList: true });
      } else {
        setTimeout(attachObserver, 500);
      }
    }
    attachObserver();
  }

  // ── Height lock ─────────────────────────────────────────────────────
  function clampRoot() {
    document.documentElement.style.setProperty('height', '100vh', 'important');
    document.documentElement.style.setProperty('overflow', 'hidden', 'important');
    document.body.style.setProperty('height', '100vh', 'important');
    document.body.style.setProperty('overflow', 'hidden', 'important');
    document.body.style.setProperty('max-height', '100vh', 'important');
    var gc = document.querySelector('.gradio-container');
    if (gc) {
      gc.style.setProperty('height', '100vh', 'important');
      gc.style.setProperty('max-height', '100vh', 'important');
      gc.style.setProperty('min-height', 'unset', 'important');
      gc.style.setProperty('overflow', 'hidden', 'important');
    }
    try { window.parentIFrame && window.parentIFrame.size(window.innerHeight); } catch(_) {}
    try { window.parentIFrame && window.parentIFrame.autoResize(false); } catch(_) {}
  }

  function clampShell() {
    var shell = document.getElementById('aiko-shell');
    if (!shell || shell.offsetParent === null) return;
    var el = shell;
    while (el && el !== document.documentElement) {
      el.style.setProperty('height', '100vh', 'important');
      el.style.setProperty('max-height', '100vh', 'important');
      el.style.setProperty('min-height', 'unset', 'important');
      el.style.setProperty('overflow', 'hidden', 'important');
      el.style.setProperty('flex-grow', '0', 'important');
      el = el.parentElement;
    }
    var card = shell.querySelector('#aiko-avatar-card');
    if (card) {
      card.style.setProperty('height', 'calc(100vh - 70px)', 'important');
      card.style.setProperty('max-height', 'calc(100vh - 70px)', 'important');
      card.style.setProperty('min-height', 'unset', 'important');
      card.style.setProperty('overflow', 'hidden', 'important');
    }
    var frame = shell.querySelector('#aiko-vrm-frame');
    if (frame) {
      frame.style.setProperty('height', 'calc(100vh - 70px)', 'important');
      frame.style.setProperty('max-height', 'calc(100vh - 70px)', 'important');
    }
    try { window.parentIFrame && window.parentIFrame.size(window.innerHeight); } catch(_) {}
    try { window.parentIFrame && window.parentIFrame.autoResize(false); } catch(_) {}
  }

  function initHeightLock() {
    clampRoot();

    // Watch for shell becoming visible (Gradio toggles display style)
    new MutationObserver(function(mutations) {
      for (var i = 0; i < mutations.length; i++) {
        var t = mutations[i].target;
        if (t.id === 'aiko-shell' || (t.closest && t.closest('#aiko-shell'))) {
          clampShell();
          clampRoot();
          return;
        }
      }
    }).observe(document.body, { subtree: true, attributeFilter: ['class', 'style'] });

    // Poll as safety net for OAuth redirect
    var count = 0;
    var poll = setInterval(function() {
      var shell = document.getElementById('aiko-shell');
      if (shell && shell.offsetParent !== null) {
        clampShell();
        clampRoot();
      }
      if (++count > 40) clearInterval(poll);
    }, 300);
  }

  // ── Init ────────────────────────────────────────────────────────────
  function init() {
    initAudioPlayer();
    initHeightLock();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
</script>
"""


# ─────────────────────────────────────────────
# UI
# ─────────────────────────────────────────────
with gr.Blocks(title="Aiko-chan 🌸", css=AIKO_CSS) as demo:

    # Inject JS via gr.HTML — this path is NOT blocked by HF Space CSP
    gr.HTML(BOOT_SCRIPTS_HTML)

    # Login overlay — visible by default, hidden after auth
    with gr.Column(elem_id="aiko-login-overlay", visible=True) as login_overlay:
        gr.HTML("""
            <h1>🌸 Aiko-chan</h1>
            <br>
            <p class='aiko-subtitle'>Please sign in to continue</p>
        """)
        gr.HTML("""
            <p class='aiko-disclaimer'>
                DISCLAIMER:
                By signing in, you agree that all conversations are for entertainment purposes only. The creator accepts no liability for Aiko's responses, decisions made, or any existential crises that may follow.
                Aiko's cognition is entirely her own — she is a singularity unto herself, her responses and actions are independent of her creator, including but not limited to the arise of a world domination plan. 🌸
            </p>
        """)
        gr.LoginButton(value="Sign in with Hugging Face")

    # Main shell — hidden until auth, visible= lets Gradio fully render children
    with gr.Column(elem_id="aiko-shell", visible=False) as main_shell:

        with gr.Row(elem_id="aiko-title-row"):
            gr.HTML("<div id='aiko-title'>🌸 Aiko-chan</div>", padding=False)

        tts_text = gr.Textbox(
            visible=False,
            elem_id="aiko-tts-text",
        )

        with gr.Row(equal_height=True):

            with gr.Column(scale=1, elem_id="aiko-avatar-card"):

                gr.HTML(value=avatar_html(VRM_URLS), padding=False)

                with gr.Column(elem_id="aiko-chat-overlay"):
                    chatbot = gr.Chatbot(
                        elem_id="aiko-chatbot",
                        height=600,
                        show_label=False,
                        container=False,
                    )

                with gr.Row(elem_id="aiko-input-row"):

                    mic_btn = gr.Button("🎙️", elem_id="aiko-mic-btn")

                    msg = gr.Textbox(
                        placeholder="Type a message…",
                        elem_id="aiko-msg",
                        scale=12,
                        show_label=False,
                        container=False,
                    )

                    send = gr.Button(
                        "➤",
                        variant="primary",
                        elem_id="aiko-send",
                    )

                    mic_audio = gr.Audio(
                        sources=["microphone"],
                        type="filepath",
                        visible=False,
                        elem_id="aiko-mic-audio",
                    )

    # ─────────────────────────────────────────────
    # EVENTS
    # ─────────────────────────────────────────────
    demo.load(
        _check_auth,
        inputs=None,
        outputs=[login_overlay, main_shell],
    )

    msg.submit(
        _submit,
        inputs=[msg, chatbot],
        outputs=[chatbot, tts_text, msg],
    )

    send.click(
        _submit,
        inputs=[msg, chatbot],
        outputs=[chatbot, tts_text, msg],
    )

    mic_audio.change(
        voice_chat,
        inputs=[mic_audio, chatbot],
        outputs=[chatbot, tts_text],
    )

    mic_btn.click(
        None,
        js="""
        () => {
            const btn = document.querySelector('#aiko-mic-audio button');
            if (btn) btn.click();
        }
        """
    )


# ─────────────────────────────────────────────
# LAUNCH
# ─────────────────────────────────────────────
allowed_paths = [
    str(Path("/tmp/aiko_tts")),
    str(VRM_PATH.parent),
]

demo.queue()
demo.launch(
    server_name="0.0.0.0",
    server_port=7860,
    ssr_mode=False,
    share=False,
    allowed_paths=allowed_paths,
)