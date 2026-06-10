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


# ── JS that wires the parent Gradio audio element to the VRM iframe ──────────
BRIDGE_JS = """
<script>
(function () {
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

  setTimeout(() => { hookAudio(); watchTtsText(); }, 1200);
})();
</script>
"""

with gr.Blocks(title="🌸 Aiko-chan", css=AIKO_CSS, fill_height=True) as demo:

    # Invisible JS bridge
    gr.HTML(BRIDGE_JS)

    with gr.Column(elem_id="aiko-shell"):

        # ── Top bar — title only, no DOCTYPE watermark ───────────────────────
        gr.HTML('<div id="aiko-topbar"><h1>🌸 AIKO-CHAN</h1></div>')

        # ── Viewer block: VRM iframe + overlaid chat + captions ──────────────
        #
        # Gradio doesn't support CSS `position: relative` containers with
        # absolutely-positioned children natively. We use a raw HTML wrapper
        # div that holds both the iframe and the chat overlay as siblings,
        # then Gradio components are placed outside for audio/input.
        #
        # The chat overlay lives *inside* a gr.HTML so Gradio's own chatbot
        # component can still be rendered separately and its messages piped
        # into the overlay via JS (see bridge below).

        with gr.Column(elem_id="aiko-viewer-wrap"):
            # VRM iframe (full width)
            gr.HTML(value=avatar_html(VRM_URLS), show_label=False)

            # Chat message overlay — absolutely positioned over the iframe (right side)
            # We render gr.Chatbot normally then relocate it via CSS.
            chatbot = gr.Chatbot(
                elem_id="aiko-chatbot",
                show_label=False,
                height=None,   # CSS controls height via the overlay
                #type="messages",
            )

        # ── Input section — below the viewer ────────────────────────────────
        with gr.Column(elem_id="aiko-input-section"):

            # Row 1: text box + send + mic record button
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

            # Row 2: waveform audio player (full width)
            audio_out = gr.Audio(
                autoplay=True,
                visible=True,
                label="🔊 Aiko",
                type="filepath",
                elem_id="aiko-audio",
                container=True,
            )

        # Hidden textbox — carries plain-text for VRM lip sync
        tts_text = gr.Textbox(
            value="",
            visible=False,
            elem_id="aiko-tts-text",
            render=True,
        )

        # ── Event wiring ─────────────────────────────────────────────────────
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