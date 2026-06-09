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

# ── Setup JS: runs once on page load ─────────────────────────────────────────
# Handles:
#   1. Input pill styling (JS class injection — most reliable cross-browser)
#   2. Exposes window.aikoSetThinking() for orb state
#   3. Aria-busy watcher as secondary fallback
SETUP_JS = """
<script>
(function() {
  // ── 1. Orb state controller ─────────────────────────────────────
  window.aikoSetThinking = function(val) {
    var wrap = document.getElementById('aiko-orb-wrap');
    if (!wrap) return;
    if (val) wrap.classList.add('thinking');
    else     wrap.classList.remove('thinking');
  };

  // ── 2. Input pill — JS-inject .aiko-input-pill on the wrapper ───
  function styleInputPill() {
    // Walk up from the textarea to find the right wrapper level
    var ta = document.querySelector('textarea[data-testid="textbox"]');
    if (!ta) return false;

    // Try parent, grandparent, great-grandparent
    var el = ta.parentElement;
    for (var i = 0; i < 4; i++) {
      if (!el) break;
      // The wrapper we want contains the textarea AND at least one button
      if (el.querySelector('button') && el.querySelector('textarea')) {
        el.classList.add('aiko-input-pill');
        // Also ensure the textarea's own wrapper has no extra border
        var innerWrap = ta.parentElement;
        if (innerWrap && innerWrap !== el) {
          innerWrap.style.background = 'transparent';
          innerWrap.style.border     = 'none';
          innerWrap.style.boxShadow  = 'none';
        }
        return true;
      }
      el = el.parentElement;
    }
    return false;
  }

  // ── 3. Aria-busy fallback for orb ───────────────────────────────
  function attachAriaWatcher() {
    var log = document.querySelector('[role="log"]');
    if (!log) { setTimeout(attachAriaWatcher, 500); return; }
    new MutationObserver(function(muts) {
      muts.forEach(function(m) {
        if (m.attributeName === 'aria-busy') {
          window.aikoSetThinking(m.target.getAttribute('aria-busy') === 'true');
        }
      });
    }).observe(log, { attributes: true });
  }

  // ── 4. Poll for .generating class as secondary orb fallback ─────
  var lastBotCount = 0;
  function pollOrb() {
    var generating = !!document.querySelector('.generating, .progress-bar, .eta-bar');
    if (generating) {
      window.aikoSetThinking(true);
    } else {
      var bots = document.querySelectorAll('#aiko-chatbot [data-testid="bot"]');
      if (bots.length !== lastBotCount) {
        window.aikoSetThinking(false);
        lastBotCount = bots.length;
      }
    }
  }

  // ── Boot ─────────────────────────────────────────────────────────
  function boot() {
    if (!styleInputPill()) {
      // Retry until Gradio renders the textarea
      var attempts = 0;
      var t = setInterval(function() {
        if (styleInputPill() || ++attempts > 40) clearInterval(t);
      }, 250);
    }
    attachAriaWatcher();
    setInterval(pollOrb, 200);
  }

  if (document.readyState !== 'loading') boot();
  else document.addEventListener('DOMContentLoaded', boot);
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


# ── JS fired by Gradio on submit (before Python runs) ────────────────────────
# This is passed to gr.ChatInterface(js=...) and executes client-side
# the moment the user submits — giving us reliable orb trigger timing.
SUBMIT_JS = """
async (message, history) => {
    window.aikoSetThinking && window.aikoSetThinking(true);
    return [message, history];
}
"""


# ── Layout ────────────────────────────────────────────────────────────────────
with gr.Blocks(title="Aiko-chan 🌸", css=CSS) as demo:

    # Setup JS (orb controller + input pill styler)
    gr.HTML(SETUP_JS)

    with gr.Row():
        # ── Left: chat column ──────────────────────────────────────────────
        with gr.Column(scale=6):

            # Orb + greeting
            gr.HTML(ORB_HEADER)

            # Speech JS
            gr.HTML(SPEECH_JS)

            # Chat interface
            # js= runs client-side on submit, before the Python fn
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