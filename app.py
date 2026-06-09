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
# Three parallel strategies so it works across Gradio 4/5/6.
ORB_THINKING_JS = """
<script>
(function() {
  function watchOrb() {
    var orbWrap = document.getElementById('aiko-orb-wrap');
    if (!orbWrap) { setTimeout(watchOrb, 300); return; }

    var isThinking = false;
    function setThinking(val) {
      if (val === isThinking) return;
      isThinking = val;
      if (val) orbWrap.classList.add('thinking');
      else orbWrap.classList.remove('thinking');
    }

    // Strategy 1: watch Gradio 5's status-tracker / progress elements
    new MutationObserver(function() {
      var active = !!document.querySelector(
        '.status-tracker:not(.hide), .progress-bar, .eta-bar, ' +
        '[data-testid="status-tracker"] .wrap, .generating'
      );
      if (active) setThinking(true);
    }).observe(document.body, {
      childList: true, subtree: true,
      attributes: true, attributeFilter: ['class', 'style']
    });

    // Strategy 2: watch aria-busy on the chatbot log div (Gradio 4-6)
    (function attach() {
      var log = document.querySelector('[role="log"]');
      if (log) {
        new MutationObserver(function(muts) {
          muts.forEach(function(m) {
            if (m.attributeName === 'aria-busy') {
              setThinking(m.target.getAttribute('aria-busy') === 'true');
            }
          });
        }).observe(log, { attributes: true });
      } else {
        setTimeout(attach, 400);
      }
    })();

    // Strategy 3: interval poll — most reliable fallback
    setInterval(function() {
      var pending = document.querySelector(
        '#aiko-chatbot .message.pending, ' +
        '#aiko-chatbot .dots, ' +
        '#aiko-chatbot .loading, ' +
        '#aiko-chatbot [data-testid="bot"].pending, ' +
        '.eta-bar, .progress-bar, .generating'
      );
      setThinking(!!pending);
    }, 250);
  }

  if (document.readyState !== 'loading') watchOrb();
  else document.addEventListener('DOMContentLoaded', watchOrb);
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