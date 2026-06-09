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


# ── Orb HTML (shown when no VRM is available, or above the chat column) ──────
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

# ── Suggestion pills ──────────────────────────────────────────────────────────
# Each pill calls sendMessage() injected below via JS
SUGGESTION_PILLS = """
<div id="aiko-suggestions">
  <span class="aiko-pill" onclick="aikoPill(this)">What are you thinking?</span>
  <span class="aiko-pill" onclick="aikoPill(this)">Tell me something</span>
  <span class="aiko-pill" onclick="aikoPill(this)">Debug help</span>
  <span class="aiko-pill" onclick="aikoPill(this)">How is Aiko feeling?</span>
</div>
<script>
(function() {
  // Click a pill → put its text into the Gradio textbox and submit
  window.aikoPill = function(el) {
    var txt = document.querySelector('textarea[data-testid="textbox"]');
    if (!txt) return;
    var nativeSetter = Object.getOwnPropertyDescriptor(
      window.HTMLTextAreaElement.prototype, 'value').set;
    nativeSetter.call(txt, el.innerText);
    txt.dispatchEvent(new Event('input', { bubbles: true }));

    // Hide the suggestions once used
    var pills = document.getElementById('aiko-suggestions');
    if (pills) pills.style.display = 'none';

    // Trigger submit after a tick
    setTimeout(function() {
      var btn = document.querySelector(
        '.input-row button, [data-testid="submit-btn"], button[aria-label="Submit"]'
      );
      if (btn) btn.click();
    }, 50);
  };

  // Auto-hide pills once user sends first real message
  document.addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      var pills = document.getElementById('aiko-suggestions');
      if (pills) pills.style.display = 'none';
    }
  }, { once: true });
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

    with gr.Row():
        # ── Left: chat column ──────────────────────────────────────────────
        with gr.Column(scale=6):

            # Orb + greeting
            gr.HTML(ORB_HEADER)

            # Suggestion pills
            gr.HTML(SUGGESTION_PILLS)

            # Chat interface — no built-in title (orb header replaces it)
            gr.ChatInterface(
                fn=chat,
                chatbot=gr.Chatbot(
                    elem_id="aiko-chatbot",
                    height=460,
                    placeholder="",       # suppress the default placeholder
                    show_label=False,
                    layout="bubble",      # bubble layout for left/right alignment
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