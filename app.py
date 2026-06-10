from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

import gradio as gr

from core.wakeup import AikoWakeup
from ui.css import AIKO_CSS
from ui.asr import transcribe_file
from ui.speak import speak_to_file
from ui.vrm import avatar_html, gradio_file_urls, resolve_vrm_path

result = AikoWakeup(text_mode=True).boot(
    on_loading=lambda k: print(f"[boot] loading: {k}"),
    on_done=lambda k: print(f"[boot]    done: {k}"),
    on_skip=lambda k: print(f"[boot]    skip: {k}"),
)
think    = result.think
memorize = result.memorize

if hasattr(think, "join_warmup"):
    think.join_warmup()

VRM_PATH = resolve_vrm_path()
VRM_URLS = gradio_file_urls(VRM_PATH)

try:
    gr.set_static_paths(paths=[VRM_PATH.parent])
except AttributeError:
    pass


def _strip_for_speech(text: str) -> str:
    """Remove markdown/search-status noise so the VRM lip sync gets plain text."""
    import re
    cleaned = re.sub(r"\n?🔍 Searching: \*.*?\*\n?", "", text)
    cleaned = re.sub(r"<think>.*?</think>", "", cleaned, flags=re.DOTALL)
    return cleaned.strip()


def _assistant_response(message: str) -> tuple[str, str | None]:
    tokens: list[str] = []

    def _cb(token):
        if token.startswith("__SEARCHING__:"):
            query = token.split(":", 1)[1].strip()
            tokens.append(f"\n🔍 Searching: *{query}*\n")
        else:
            tokens.append(token)

    think.chat(message, token_callback=_cb)
    text  = "".join(tokens)
    audio = speak_to_file(text)
    print(f"[chat] audio path: {audio}")
    return text, audio


def text_chat(message, history):
    history = history or []
    message = (message or "").strip()
    if not message:
        return history, None, "", ""
    text, audio = _assistant_response(message)
    history.append({"role": "user",      "content": message})
    history.append({"role": "assistant", "content": text})
    return history, _strip_for_speech(text), audio, ""


def voice_chat(audio_path, history):
    history = history or []
    if not audio_path:
        return history, None, None, ""
    transcript = transcribe_file(audio_path)
    if not transcript:
        return history, None, None, ""
    text, audio = _assistant_response(transcript)
    history.append({"role": "user",      "content": f"🎙️ {transcript}"})
    history.append({"role": "assistant", "content": text})
    return history, _strip_for_speech(text), audio, None


# ── Viewer HTML: iframe + chat overlay div + caption bar, all in one fixed block
def viewer_html(vrm_html: str) -> str:
    return f"""
<div id="aiko-viewer-wrap">
  {vrm_html}
  <div id="aiko-chat-overlay">
    <div id="aiko-msg-list"></div>
  </div>
</div>
"""


BRIDGE_JS = """
<script>
(function () {
  /* ── VRM postMessage bridge ── */
  function postToVrm(text) {
    const frame = document.getElementById('aiko-vrm-frame');
    if (!frame) return;
    frame.contentWindow.postMessage({ ttsText: text, playNow: true }, '*');
  }

  function hookAudio() {
    const audio = document.querySelector('#aiko-audio audio');
    if (!audio) { setTimeout(hookAudio, 600); return; }
    ['play', 'playing'].forEach(evt => {
      audio.addEventListener(evt, () => {
        setTimeout(() => {
          const el = document.querySelector('#aiko-tts-text textarea');
          if (el && el.value) postToVrm(el.value);
        }, 150);
      });
    });
  }

  function watchTtsText() {
    const container = document.querySelector('#aiko-tts-text');
    if (!container) { setTimeout(watchTtsText, 600); return; }
    const observer = new MutationObserver(() => {
      const el = container.querySelector('textarea');
      if (el && el.value) postToVrm(el.value);
    });
    observer.observe(container, { childList: true, subtree: true, characterData: true, attributes: true });
  }

  /* ── Chat overlay: mirror hidden gr.Chatbot into #aiko-msg-list ── */
  function escapeHtml(s) {
    return String(s)
      .replace(/&/g,'&amp;').replace(/</g,'&lt;')
      .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  function syncMessages() {
    const msgList = document.getElementById('aiko-msg-list');
    if (!msgList) return;

    // Gradio renders messages as divs with data-testid="user" / "bot"
    // inside #aiko-chatbot-hidden
    const bubbles = document.querySelectorAll(
      '#aiko-chatbot-hidden [data-testid="user"], #aiko-chatbot-hidden [data-testid="bot"]'
    );
    if (!bubbles.length) return;

    msgList.innerHTML = '';
    bubbles.forEach(b => {
      const isUser = b.dataset.testid === 'user';
      const div = document.createElement('div');
      div.className = 'aiko-msg ' + (isUser ? 'aiko-msg-user' : 'aiko-msg-bot');
      div.innerHTML = b.innerHTML;   // preserve markdown-rendered HTML
      msgList.appendChild(div);
    });

    // Scroll to bottom
    msgList.scrollTop = msgList.scrollHeight;
  }

  function watchChatbot() {
    const bot = document.getElementById('aiko-chatbot-hidden');
    if (!bot) { setTimeout(watchChatbot, 800); return; }
    const obs = new MutationObserver(syncMessages);
    obs.observe(bot, { childList: true, subtree: true });
    syncMessages();
  }

  setTimeout(() => {
    hookAudio();
    watchTtsText();
    watchChatbot();
  }, 1400);
})();
</script>
"""


with gr.Blocks(title="🌸 Aiko-chan", css=AIKO_CSS) as demo:   # no fill_height

    gr.HTML(BRIDGE_JS)

    with gr.Column(elem_id="aiko-shell"):

        # Top bar
        gr.HTML('<div id="aiko-topbar"><h1>🌸 AIKO-CHAN</h1></div>')

        # Viewer: fixed-height HTML block — no Gradio children that can stretch it
        gr.HTML(value=viewer_html(avatar_html(VRM_URLS)))

        # Input row: textbox + send + mic  (below the viewer)
        with gr.Row(elem_id="aiko-input-row"):
            msg = gr.Textbox(
                placeholder="Type a message…",
                show_label=False,
                scale=11,
                container=False,
            )
            send = gr.Button("➤", variant="primary", scale=1, elem_id="aiko-send")
            voice_in = gr.Audio(
                sources=["microphone"],
                type="filepath",
                show_label=False,
                scale=2,
                elem_id="aiko-mic",
                container=False,
            )

        # Waveform audio player (below inputs)
        audio_out = gr.Audio(
            autoplay=True,
            visible=True,
            label="🔊 Aiko",
            type="filepath",
            elem_id="aiko-audio",
            container=True,
        )

        # Hidden Gradio chatbot — real state lives here, overlay mirrors it via JS
        chatbot = gr.Chatbot(
            elem_id="aiko-chatbot-hidden",
            show_label=False,
            height=1,            # collapse to near-zero; CSS hides it fully
            #type="messages",
            visible=False,
        )

        # Hidden TTS text carrier for lip sync
        tts_text = gr.Textbox(
            value="",
            visible=False,
            elem_id="aiko-tts-text",
            render=True,
        )

        # Event wiring
        msg.submit(text_chat,  [msg, chatbot], [chatbot, tts_text, audio_out, msg])
        send.click(text_chat,  [msg, chatbot], [chatbot, tts_text, audio_out, msg])
        voice_in.change(voice_chat, [voice_in, chatbot], [chatbot, tts_text, audio_out, voice_in])


allowed_paths = [str(Path("/tmp/aiko_tts")), str(VRM_PATH.parent)]

demo.launch(
    server_name="0.0.0.0",
    server_port=7860,
    ssr_mode=False,
    share=False,
    allowed_paths=allowed_paths,
)