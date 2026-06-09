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
# Drop-in replacement for ORB_THINKING_JS in app.py

ORB_THINKING_JS = """
<script>
(function() {
  function watchOrb() {
    var orbWrap = document.getElementById('aiko-orb-wrap');
    if (!orbWrap) { setTimeout(watchOrb, 300); return; }

    var isThinking = false;
    var clearTimer  = null;

    function setThinking(val) {
      if (val === isThinking) return;
      isThinking = val;
      if (val) {
        orbWrap.classList.add('thinking');
      } else {
        orbWrap.classList.remove('thinking');
      }
    }

    // ── Strategy 1: hook the submit button click ───────────────────
    // Fire thinking=true the instant the user submits; this works even
    // when the Python fn is synchronous/blocking (no streaming DOM cues).
    function attachSubmitHook() {
      // Gradio's submit button lives inside the chatinterface form area
      var btn = document.querySelector(
        '#aiko-chatbot ~ * button[aria-label="Submit"],'+
        '.submit-btn, button[data-testid="submit-btn"],'+
        'button.primary[type="submit"]'
      );
      // Broader fallback: any send/submit button near the textbox
      if (!btn) {
        btn = document.querySelector(
          'button svg[data-testid="send-btn"], ' +
          '[data-testid="submit-btn"]'
        );
        if (btn) btn = btn.closest('button');
      }
      // Final fallback: the Gradio ChatInterface submit button
      if (!btn) {
        var btns = document.querySelectorAll('button');
        for (var i = 0; i < btns.length; i++) {
          var svg = btns[i].querySelector('svg');
          if (svg && (btns[i].title === 'Submit' || btns[i].getAttribute('aria-label') === 'Submit')) {
            btn = btns[i]; break;
          }
        }
      }
      if (btn && !btn._aikoHooked) {
        btn._aikoHooked = true;
        btn.addEventListener('click', function() {
          setThinking(true);
        });
      }
      // Also hook Enter key in the textarea
      var ta = document.querySelector('textarea[data-testid="textbox"]');
      if (ta && !ta._aikoHooked) {
        ta._aikoHooked = true;
        ta.addEventListener('keydown', function(e) {
          if (e.key === 'Enter' && !e.shiftKey) setThinking(true);
        });
      }
    }
    attachSubmitHook();
    // Re-run hook attempt a few times in case DOM isn't ready yet
    setTimeout(attachSubmitHook, 800);
    setTimeout(attachSubmitHook, 2000);

    // ── Strategy 2: aria-busy on the chatbot log (Gradio 4-6) ──────
    (function attachAriaWatcher() {
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
        setTimeout(attachAriaWatcher, 400);
      }
    })();

    // ── Strategy 3: MutationObserver on body for .generating ───────
    new MutationObserver(function() {
      var active = !!document.querySelector(
        '.status-tracker:not(.hide), .progress-bar, .eta-bar, .generating,' +
        '[data-testid="status-tracker"] .wrap'
      );
      if (active) setThinking(true);
    }).observe(document.body, {
      childList: true, subtree: true,
      attributes: true, attributeFilter: ['class', 'style']
    });

    // ── Strategy 4: interval poll — counts new bot messages ────────
    // When a new bot message appears after we went thinking=true, clear.
    var lastBotCount = 0;
    setInterval(function() {
      var botMsgs = document.querySelectorAll('#aiko-chatbot [data-testid="bot"]');
      var count   = botMsgs.length;

      // Still generating?
      var pending = !!document.querySelector(
        '#aiko-chatbot .message.pending, #aiko-chatbot .dots,' +
        '#aiko-chatbot .loading, .eta-bar, .progress-bar, .generating'
      );

      if (pending) {
        setThinking(true);
      } else if (isThinking && count > lastBotCount) {
        // New bot message landed → done
        setThinking(false);
      } else if (!pending && !isThinking) {
        // Idle — just keep lastBotCount in sync
      }
      lastBotCount = count;
    }, 200);
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