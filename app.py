from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

import gradio as gr
import time

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
think = result.think
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


import re

_SENTENCE_END = re.compile(r'(?<=[.!?。！？\n])\s*')


def _split_ready_sentences(buffer: str) -> tuple[list[str], str]:
    """Split buffer into complete sentences + remaining partial text."""
    parts = _SENTENCE_END.split(buffer)
    if len(parts) <= 1:
        return [], buffer
    *complete, remainder = parts
    return [p for p in complete if p.strip()], remainder


def _stream_response(message: str, history: list):
    """Generator: yields (history, tts_text, audio_path).

    Immediately emits the user turn so it appears before inference begins,
    then streams assistant tokens sentence-by-sentence for TTS.
    tts_text carries "EMOTION:<name>|<sentence>" so the JS can split and
    drive both lip-sync and facial expression on the VRM.
    """
    # ── 1. Show user message immediately, AI turn shows cursor ───────────
    history = list(history) + [
        {"role": "user", "content": message},
        {"role": "assistant", "content": "▋"},
    ]
    yield history, "", None

    buffer = ""
    full_text = ""

    def _cb(token):
        nonlocal buffer, full_text
        if token.startswith("__SEARCHING__:"):
            query = token.split(":", 1)[1].strip()
            note = f"\n🔍 Searching: *{query}*\n"
            buffer += note
            full_text += note
        else:
            buffer += token
            full_text += token

    # ── 2. Run think.chat in background thread ────────────────────────────
    import threading
    done = threading.Event()
    error = {}

    def _run():
        try:
            think.chat(message, token_callback=_cb)
        except Exception as e:
            error["e"] = e
        finally:
            done.set()

    t = threading.Thread(target=_run, daemon=True)
    t.start()

    # ── 3. Stream sentences as they complete ─────────────────────────────
    while not done.is_set() or buffer.strip():
        sentences, buffer = _split_ready_sentences(buffer)
        for sentence in sentences:
            clean = _strip_for_speech(sentence)
            if not clean:
                continue
            history[-1]["content"] = full_text + ("▋" if not done.is_set() else "")
            audio, emotion = speak_to_file(clean)
            tts_payload = f"EMOTION:{emotion}|{clean}"
            yield history, tts_payload, audio
        if not sentences:
            if full_text:
                history[-1]["content"] = full_text + "▋"
                yield history, "", None
            time.sleep(0.05)

    # ── 4. Flush trailing partial sentence ───────────────────────────────
    if buffer.strip():
        clean = _strip_for_speech(buffer)
        history[-1]["content"] = full_text
        if clean:
            audio, emotion = speak_to_file(clean)
            tts_payload = f"EMOTION:{emotion}|{clean}"
            yield history, tts_payload, audio
        else:
            yield history, "", None

    if error:
        raise error["e"]

    # ── 5. Final: full text, no cursor ────────────────────────────────────
    history[-1]["content"] = full_text
    yield history, "", None


def text_chat(message: str, history: list):
    """Handle text input."""
    history = history or []
    message = (message or "").strip()
    if not message:
        yield history, None, None
        return
    yield from _stream_response(message, history)


def voice_chat(audio_path, history):
    history = history or []
    if not audio_path:
        yield history, None, None
        return
    transcript = transcribe_file(audio_path)
    if not transcript:
        yield history, None, None
        return
    for h, tts, audio in _stream_response(transcript, history):
        if h and h[-2]["content"] == transcript:
            h[-2]["content"] = f"🎙️ {transcript}"
        yield h, tts, audio


with gr.Blocks(title="Aiko-chan 🌸", css=AIKO_CSS, fill_height=True) as demo:
    with gr.Column(elem_id="aiko-shell"):
        gr.HTML("""
            <div id="aiko-title">🌸 Aiko-chan</div>
            <script>
            (function() {

              // ── Create/ensure single emotion label exists ─────────────
              function ensureEmotionLabel() {
                const card = document.getElementById('aiko-avatar-card');
                if (!card) { setTimeout(ensureEmotionLabel, 600); return; }
                // Remove any existing copies (covers SSR/hydration dupes)
                document.querySelectorAll('#aiko-emotion-label').forEach(el => el.remove());
                const label = document.createElement('div');
                label.id = 'aiko-emotion-label';
                label.textContent = 'RELAXED';
                card.prepend(label);
              }

              // ── Emotion label ──────────────────────────────────────────
              function setEmotionLabel(emotion) {
                const el = document.getElementById('aiko-emotion-label');
                if (!el) return;
                el.textContent = emotion ? emotion.toUpperCase() : '';
              }

              // ── Post to VRM iframe ─────────────────────────────────────
              function postToVrm(text, emotion) {
                const frame = document.getElementById('aiko-vrm-frame');
                if (!frame) return;
                frame.contentWindow.postMessage(
                  { ttsText: text, playNow: true, expression: emotion || "neutral" },
                  '*'
                );
                setEmotionLabel(emotion || 'neutral');
              }

              // ── Parse EMOTION:<name>|<text> payload ───────────────────
              function parseEmotionPayload(raw) {
                if (!raw) return null;
                const m = raw.match(/^EMOTION:([^|]+)\|(.*)$/s);
                if (m) return { emotion: m[1].trim(), text: m[2].trim() };
                return { emotion: 'neutral', text: raw };
              }

              // ── Hook audio element to drive VRM on play ───────────────
              function hookAudio() {
                const audio = document.querySelector('#aiko-audio audio');
                if (!audio) { setTimeout(hookAudio, 600); return; }
                ['play', 'playing'].forEach(evt => {
                  audio.addEventListener(evt, () => {
                    setTimeout(() => {
                      const el = document.querySelector('#aiko-tts-text textarea');
                      if (!el || !el.value) return;
                      const parsed = parseEmotionPayload(el.value);
                      if (parsed) postToVrm(parsed.text, parsed.emotion);
                    }, 80);
                  });
                });
              }

              // ── Watch tts-text for changes and drive VRM immediately ──
              function watchTtsText() {
                const container = document.querySelector('#aiko-tts-text');
                if (!container) { setTimeout(watchTtsText, 600); return; }

                let lastValue = '';
                const observer = new MutationObserver(() => {
                  const el = container.querySelector('textarea');
                  if (!el) return;
                  const raw = el.value;
                  if (!raw || raw === lastValue) return;
                  lastValue = raw;
                  const parsed = parseEmotionPayload(raw);
                  if (parsed && parsed.emotion && parsed.emotion !== 'neutral') {
                    // Drive expression change immediately (don't wait for audio)
                    const frame = document.getElementById('aiko-vrm-frame');
                    if (frame) {
                      frame.contentWindow.postMessage(
                        { expression: parsed.emotion },
                        '*'
                      );
                    }
                    setEmotionLabel(parsed.emotion);
                  }
                });
                observer.observe(container, { childList: true, subtree: true, characterData: true, attributes: true });
              }

              // ── Auto-scroll chatbot to bottom on new content ──────────
              function setupChatScroll() {
                const chatbot = document.querySelector('#aiko-chatbot');
                if (!chatbot) { setTimeout(setupChatScroll, 800); return; }
                const scrollEl = chatbot.querySelector('[class*="wrap"]') || chatbot;
                const autoScroll = new MutationObserver(() => {
                  scrollEl.scrollTop = scrollEl.scrollHeight;
                });
                autoScroll.observe(scrollEl, { childList: true, subtree: true });
              }

              // ── Hook mic button ───────────────────────────────────────
              function hookMicBtn() {
                const btn = document.querySelector('#aiko-mic-btn button');
                const recorderWrap = document.querySelector('#aiko-mic-audio');
                if (!btn || !recorderWrap) { setTimeout(hookMicBtn, 600); return; }

                recorderWrap.style.position = 'fixed';
                recorderWrap.style.opacity = '0';
                recorderWrap.style.pointerEvents = 'none';
                recorderWrap.style.display = 'block';

                btn.addEventListener('click', () => {
                  const recBtn = recorderWrap.querySelector('button');
                  if (recBtn) recBtn.click();
                });
              }

              setTimeout(() => {
                ensureEmotionLabel();
                hookAudio();
                watchTtsText();
                setupChatScroll();
                hookMicBtn();
              }, 1200);

            })();
            </script>
            """)

        with gr.Row(equal_height=True):
            with gr.Column(scale=1, elem_id="aiko-avatar-card"):
                # Emotion label is created dynamically via JS below
                # (avoids Gradio SSR/hydration double-render of gr.HTML)

                gr.HTML(value=avatar_html(VRM_URLS), show_label=False)
                audio_out = gr.Audio(
                    autoplay=True, visible=True, label="🔊 Aiko",
                    type="filepath", elem_id="aiko-audio", container=False,
                )
                tts_text = gr.Textbox(value="", visible=False, elem_id="aiko-tts-text", render=True)

                with gr.Column(elem_id="aiko-chat-overlay"):
                    chatbot = gr.Chatbot(
                        elem_id="aiko-chatbot",
                        show_label=False,
                        height=600,
                        #type="messages",
                    )

                with gr.Row(elem_id="aiko-input-row"):
                    mic_btn = gr.Button("🎙️", scale=0, elem_id="aiko-mic-btn", min_width=0)
                    msg = gr.Textbox(
                        placeholder="Type a message…",
                        show_label=False,
                        scale=12,
                        container=False,
                        elem_id="aiko-msg",
                    )
                    send = gr.Button("➤", variant="primary", scale=0, elem_id="aiko-send", min_width=0)

                mic_audio = gr.Audio(
                    sources=["microphone"],
                    type="filepath",
                    label="",
                    elem_id="aiko-mic-audio",
                    container=False,
                    show_label=False,
                    visible=False,
                )

                # ── Two-step submit: capture → clear → stream ─────────────
                # Only touch the `msg` textbox on the FIRST yield (clearing it).
                # Subsequent yields use gr.skip() so we never re-clobber
                # whatever the user has started typing for their next turn.

                def _submit(message, history):
                    """Capture message, clear box once, then stream."""
                    message = (message or "").strip()
                    if not message:
                        yield gr.update(value=""), history, "", None
                        return
                
                    first = True
                
                    for h, tts, audio in text_chat(message, history):
                        if first:
                            # Clear the textbox only once
                            yield gr.update(value=""), h, tts, audio
                            first = False
                        else:
                            # Leave whatever the user is typing alone
                            yield gr.skip(), h, tts, audio

                for trigger in (msg.submit, send.click):
                    trigger(
                        _submit,
                        inputs=[msg, chatbot],
                        outputs=[msg, chatbot, tts_text, audio_out],
                    )

                mic_audio.change(voice_chat, [mic_audio, chatbot], [chatbot, tts_text, audio_out])

allowed_paths = [str(Path("/tmp/aiko_tts")), str(VRM_PATH.parent)]

demo.launch(
    server_name="0.0.0.0",
    server_port=7860,
    ssr_mode=False,
    share=False,
    allowed_paths=allowed_paths,
)