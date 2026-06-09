from dotenv import load_dotenv
load_dotenv()

import gradio as gr
from core.wakeup import AikoWakeup
from ui.css import CSS
from ui.speech import SPEECH_JS
from ui.vrm_viewer import VRM_VIEWER

result = AikoWakeup(text_mode=True).boot(
    on_loading=lambda k: print(f"[boot] loading: {k}"),
    on_done   =lambda k: print(f"[boot]    done: {k}"),
    on_skip   =lambda k: print(f"[boot]    skip: {k}"),
)
think    = result.think
memorize = result.memorize

if hasattr(think, "join_warmup"):
    think.join_warmup()


# ── Orb header ────────────────────────────────────────────────────────────────
ORB_HEADER = """
<div id="aiko-orb-section">
  <div id="aiko-orb-wrap">
    <div id="aiko-orb-ring-outer"></div>
    <div id="aiko-orb-ring-inner"></div>
    <div id="aiko-orb"></div>
  </div>
  <div id="aiko-greeting">
    <h2>Hi Oppa! How can I help you today?</h2>
    <p>AI companion &middot; always here</p>
  </div>
</div>
"""

# ── Orb thinking animation JS ─────────────────────────────────────────────────
# Watches for Gradio's pending/generating state and toggles .thinking on the orb.
# Gradio 6 adds aria-busy="true" on the chatbot log div while streaming.
ORB_THINKING_JS = """
<script>
(function() {
  function watchOrb() {
    var orbWrap = document.getElementById('aiko-orb-wrap');
    if (!orbWrap) { setTimeout(watchOrb, 300); return; }

    // Observe the chatbot log div for aria-busy changes
    var mo = new MutationObserver(function(mutations) {
      mutations.forEach(function(m) {
        if (m.type === 'attributes' && m.attributeName === 'aria-busy') {
          var busy = m.target.getAttribute('aria-busy') === 'true';
          if (busy) {
            orbWrap.classList.add('thinking');
          } else {
            orbWrap.classList.remove('thinking');
          }
        }
      });
    });

    // The chatbot log has role="log" aria-live="polite"
    function attachObserver() {
      var log = document.querySelector('[role="log"][aria-label="chatbot conversation"]');
      if (log) {
        mo.observe(log, { attributes: true });
      } else {
        setTimeout(attachObserver, 400);
      }
    }
    attachObserver();

    // Fallback: also watch for the loading spinner appearing/disappearing
    var spinnerObs = new MutationObserver(function() {
      var spinner = document.querySelector('#aiko-chatbot .loading-spinner');
      var dots    = document.querySelector('#aiko-chatbot .dots');
      if (spinner || dots) {
        orbWrap.classList.add('thinking');
      } else {
        orbWrap.classList.remove('thinking');
      }
    });
    var chatbot = document.getElementById('aiko-chatbot');
    if (chatbot) {
      spinnerObs.observe(chatbot, { childList: true, subtree: true });
    }
  }
  document.addEventListener('DOMContentLoaded', watchOrb);
  // Also try immediately in case DOM is already ready
  if (document.readyState !== 'loading') watchOrb();
})();
</script>
"""


# ── Chat function ─────────────────────────────────────────────────────────────
def chat(message, history):
    tokens = []

    def _cb(token):
        if token.startswith("__SEARCHING__:"):
            query = token.split(":", 1)[1].strip()
            tokens.append(f"\n🔍 *Searching: {query}*\n")
        else:
            tokens.append(token)

    think.chat(message, token_callback=_cb)
    return "".join(tokens)


# ── Layout ────────────────────────────────────────────────────────────────────
with gr.Blocks(title="Aiko-chan 🌸", css=CSS) as demo:

    # Speech JS (VAD, TTS hooks)
    gr.HTML(SPEECH_JS)

    # Orb thinking JS
    gr.HTML(ORB_THINKING_JS)

    with gr.Row():
        # ── Left: chat column ──────────────────────────────────────────────
        with gr.Column(scale=6):

            # Orb + greeting (above chat, no suggestions)
            gr.HTML(ORB_HEADER)

            # Chat interface
            gr.ChatInterface(
                fn=chat,
                chatbot=gr.Chatbot(
                    elem_id="aiko-chatbot",
                    height=500,
                    placeholder="",
                    show_label=False,
                    layout="bubble",
                    avatar_images=(None, None),
                ),
                textbox=gr.Textbox(
                    placeholder="Message Aiko...",
                    show_label=False,
                    lines=1,
                    max_lines=6,
                    submit_btn=True,
                    stop_btn=True,
                    container=False,
                ),
                title=None,
                fill_height=False,
            )

        # ── Right: VRM viewer column ───────────────────────────────────────
        with gr.Column(scale=4, elem_id="aiko-col"):
            gr.HTML(VRM_VIEWER)


demo.launch(
    server_name="0.0.0.0",
    server_port=7860,
    ssr_mode=False,
    share=False,
    allowed_paths=["static"],
)