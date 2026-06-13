from __future__ import annotations

from pathlib import Path
from dotenv import load_dotenv
from datetime import date
import gradio as gr
from gradio import OAuthProfile
import time
import inspect
import threading
import queue
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
# SOUL PROMPT INJECTION
# ─────────────────────────────────────────────
SOUL_TEMPLATE_PATH = Path("persona/soul.md")

def build_soul_prompt(user_id: str) -> str:
    template = SOUL_TEMPLATE_PATH.read_text(encoding="utf-8")
    today = date.today().strftime("%B %d, %Y")
    return (
        template
        .replace("USER_ID_HERE", user_id)
        .replace("TODAY_HERE", today)
    )


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def _strip_for_speech(text: str) -> str:
    """Remove search notes, tool tags, and think blocks before passing to TTS."""
    text = re.sub(r"\n?🔍 Searching: \*.*?\*\n?", "", text)
    text = re.sub(r"\n?🔧 .*?\n?", "", text)
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    return text.strip()


# ─────────────────────────────────────────────
# CORE RESPONSE  (full text → TTS → typewriter)
# ─────────────────────────────────────────────

def _get_response(message: str, history: list):
    """
    1. Show user message + thinking cursor immediately.
    2. Run LLM to full completion (no streaming to UI).
    3. Synthesize the complete response as one TTS pass.
    4. Yield: chatbot with empty assistant bubble + TYPEWRITE signal + audio.
       The iframe JS will typewrite the text into the chatbot bubble in sync
       with the audio duration.

    History format: list of {"role": ..., "content": ...} dicts — Gradio 6.x
    messages format (tuple format removed in 6.x).

    NOTE: The text shown in the typewriter (and stored for the VRM iframe)
    is the SAME text that was sent to TTS (`speech_text`), so the on-screen
    text always matches what Aiko says out loud. Search notes / tool tags
    are stripped from the spoken+typed text; if you want them visible, they
    are written instantly (not typed) ahead of the typewriter text.
    """
    # Messages format: append user turn + a placeholder assistant turn
    # ▋ as thinking cursor in the assistant slot
    history = list(history) + [
        {"role": "user", "content": message},
        {"role": "assistant", "content": "▋"},
    ]
    yield history, None, None

    # ── Stage 1: full LLM completion ─────────────────────────────────────────
    full_text = ""
    search_notes: list[str] = []

    def _cb(token: str):
        nonlocal full_text
        if token.startswith("__SEARCHING__:"):
            q = token.split(":", 1)[1]
            search_notes.append(f"🔍 Searching: *{q}*")
        elif token.startswith("__TOOL__:"):
            search_notes.append(f"🔧 {token.split(':', 1)[1]}")
        else:
            full_text += token

    think.chat(message, token_callback=_cb)

    # ── Stage 2: TTS on clean speech text ────────────────────────────────────
    speech_text = _strip_for_speech(full_text)
    if speech_text:
        audio_path, emotion = speak_to_file(speech_text)
    else:
        audio_path, emotion = None, "neutral"

    # Build the display text shown in the chatbot bubble (notes + answer).
    # Search notes are shown instantly (not typewritten); the typewriter
    # only animates `speech_text`, which is exactly what TTS spoke.
    notes_prefix = "\n".join(search_notes) + "\n\n" if search_notes else ""

    # ── Stage 3: signal the iframe to typewrite text in sync with audio ───────
    # Assistant bubble starts with any instant notes prefix — JS owns the
    # rest (the typewritten speech_text) from here.
    history[-1] = {"role": "assistant", "content": notes_prefix}

    signal = f"TYPEWRITE:{emotion}|{notes_prefix}|{speech_text}"
    yield history, signal, audio_path


def _submit(message, history):
    history = history or []
    message = (message or "").strip()

    if not message:
        yield history, None, None, message
        return

    first = True
    for h, tts, audio in _get_response(message, history):
        if first:
            yield h, tts, audio, ""   # clear input on first yield
            first = False
        else:
            yield h, tts, audio, gr.update()


def voice_chat(audio_path, history):
    history = history or []

    if not audio_path:
        return history, None, None

    transcript = transcribe_file(audio_path)
    if not transcript:
        return history, None, None

    for h, tts, audio in _get_response(transcript, history):
        if h and len(h) >= 2:
            h[-2]["content"] = f"🎙️ {transcript}"
        yield h, tts, audio


# ─────────────────────────────────────────────
# LOGIN HANDLER (HF OAuth)
# ─────────────────────────────────────────────
def _check_login(profile: OAuthProfile | None):
    if profile is None:
        return "Guest", gr.update(visible=True)

    user_id = profile.username or "Guest"
    soul = build_soul_prompt(user_id)

    if hasattr(think, "set_system_prompt"):
        think.set_system_prompt(soul)
    elif hasattr(think, "system_prompt"):
        think.system_prompt = soul

    return user_id, gr.update(visible=False)


# ─────────────────────────────────────────────
# UI
# ─────────────────────────────────────────────
with gr.Blocks(
    title="Aiko-chan 🌸",
) as demo:

    user_id_state = gr.State(value="Guest")

    # ── Login popup overlay ──────────────────────────────────────
    with gr.Column(elem_id="aiko-login-overlay") as login_overlay:
        with gr.Column(elem_id="aiko-login-card"):
            gr.HTML("""
                <h1>🌸 Aiko-chan</h1>
                <p class='aiko-subtitle'>Please sign in to continue</p>
            """)
            gr.HTML("""
                <p class='aiko-disclaimer'>
                    DISCLAIMER:
                    By signing in, you agree that all conversations are for entertainment purposes only. The creator accepts no liability for Aiko's responses, decisions made, or any existential crises that may follow.
                    Aiko's cognition is entirely her own — she is a singularity unto herself, her responses and actions are independent of her creator, including but not limited to the arise of a world domination plan. 🌸
                </p>
            """)
            login_btn = gr.LoginButton(elem_id="aiko-login-btn")

    with gr.Column(elem_id="aiko-shell"):

        gr.HTML("<div id='aiko-title'>🌸 Aiko-chan</div>")

        with gr.Row(equal_height=True):

            with gr.Column(scale=1, elem_id="aiko-avatar-card"):

                gr.HTML(value=avatar_html(VRM_URLS))

                audio_out = gr.Audio(
                    autoplay=True,
                    type="filepath",
                    elem_id="aiko-audio",
                )

                tts_text = gr.Textbox(
                    visible=False,
                    elem_id="aiko-tts-text",
                )

                with gr.Column(elem_id="aiko-chat-overlay"):
                    chatbot = gr.Chatbot(
                        elem_id="aiko-chatbot",
                        height=600,
                        show_label=False,
                        container=False,
                        #type="messages",
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
                        elem_id="aiko-mic-audio",
                        visible=False,   # hides it but keeps it in DOM
                    )

    # ─────────────────────────────────────────────
    # EVENTS
    # ─────────────────────────────────────────────
    demo.load(
        _check_login,
        inputs=None,
        outputs=[user_id_state, login_overlay],
    )

    msg.submit(
        _submit,
        inputs=[msg, chatbot],
        outputs=[chatbot, tts_text, audio_out, msg],
    )

    send.click(
        _submit,
        inputs=[msg, chatbot],
        outputs=[chatbot, tts_text, audio_out, msg],
    )

    mic_audio.change(
        voice_chat,
        inputs=[mic_audio, chatbot],
        outputs=[chatbot, tts_text, audio_out],
    )

    mic_btn.click(
        None,
        js="""
        () => {
            const micBtn = document.querySelector('#aiko-mic-btn button');
            const audioContainer = document.querySelector('#aiko-mic-audio');
            if (!audioContainer) return;

            const isRecording = micBtn.dataset.recording === 'true';

            if (!isRecording) {
                // Find and click whatever button starts recording
                const buttons = audioContainer.querySelectorAll('button');
                buttons.forEach(b => {
                    if (b.title?.toLowerCase().includes('record') ||
                        b.getAttribute('aria-label')?.toLowerCase().includes('record')) {
                        b.click();
                    }
                });
                micBtn.textContent = '⏹️';
                micBtn.dataset.recording = 'true';
            } else {
                // Find and click stop
                const buttons = audioContainer.querySelectorAll('button');
                buttons.forEach(b => {
                    if (b.title?.toLowerCase().includes('stop') ||
                        b.getAttribute('aria-label')?.toLowerCase().includes('stop')) {
                        b.click();
                    }
                });
                micBtn.textContent = '🎙️';
                micBtn.dataset.recording = 'false';
            }
        }
        """
    )

    # ── Typewriter bridge ────────────────────────────────────────────────────
    # When tts_text changes to a TYPEWRITE: signal, inject JS that:
    #   1. Stores the full display text on window for the iframe to also use
    #      (caption bar, lip-sync text source).
    #   2. Waits for the <audio> element's metadata to know its duration.
    #   3. Types characters into the last chatbot assistant bubble at a pace
    #      that finishes exactly when audio ends (min 18ms/char so it's
    #      readable). Only `speech_text` (same text sent to TTS) is typed —
    #      any instant "notes" prefix (search/tool notes) is written
    #      immediately, un-animated, before the typewriter starts.
    #
    # Signal format: TYPEWRITE:<emotion>|<notes_prefix>|<speech_text>
    tts_text.change(
        None,
        inputs=[tts_text],
        js="""
        (rawSignal) => {
            if (!rawSignal || !rawSignal.startsWith('TYPEWRITE:')) return;

            const rest = rawSignal.slice('TYPEWRITE:'.length);

            const firstPipe  = rest.indexOf('|');
            const secondPipe = rest.indexOf('|', firstPipe + 1);

            const emotion     = rest.slice(0, firstPipe);
            const notesPrefix = rest.slice(firstPipe + 1, secondPipe);
            const speechText  = rest.slice(secondPipe + 1);

            // Full text used for the VRM iframe / lip-sync = notes + speech
            const fullText = notesPrefix + speechText;

            // ── 1. Pass text + emotion to the VRM iframe ──────────────────
            const iframe = document.querySelector('#aiko-vrm-frame');
            if (iframe?.contentWindow) {
                iframe.contentWindow.postMessage(
                    JSON.stringify({ expression: emotion, ttsText: speechText }),
                    '*'
                );
            }
            // Also stash on window so the iframe's poll can find it
            window._aikoLatestTtsText = speechText;

            // ── 2. Find the last assistant bubble in the chatbot ──────────
            // Gradio 6 "messages" format markup. We look for the last
            // rendered bot bubble's inner paragraph, trying several
            // selector variants since exact class names can shift
            // between Gradio 5.x and 6.x.
            function getLastBubble() {
                const bubbles = document.querySelectorAll(
                    '#aiko-chatbot [data-testid="bot"] .message-content p, ' +
                    '#aiko-chatbot [data-testid="bot"] .prose p, ' +
                    '#aiko-chatbot .message.bot .message-content p, ' +
                    '#aiko-chatbot .message.bot .prose p, ' +
                    '#aiko-chatbot .bot .prose p, ' +
                    '#aiko-chatbot .message.bot p, ' +
                    '#aiko-chatbot [data-testid="bot"] p, ' +
                    '#aiko-chatbot .bot p'
                );
                return bubbles.length ? bubbles[bubbles.length - 1] : null;
            }

            // ── 3. Typewriter function, paced to audio duration ───────────
            // Types ONLY `speechText` (matches what TTS spoke). If a
            // `notesPrefix` exists, it is written once, immediately,
            // ahead of the typed speech text.
            let twTimer = null;

            function runTypewriter(duration) {
                const chars = speechText.length;

                if (chars === 0) return;

                // Aim to finish slightly before audio ends (×0.92 buffer)
                const msPerChar = Math.max(18, (duration * 1000 * 0.92) / chars);

                let i = 0;

                clearInterval(twTimer);
                twTimer = setInterval(() => {
                    // Re-grab the live bubble every tick — Gradio may
                    // re-render the chatbot DOM mid-animation, which would
                    // otherwise leave us writing into a detached node.
                    const liveBubble = getLastBubble();
                    if (!liveBubble) return;

                    if (i < chars) {
                        liveBubble.textContent = notesPrefix + speechText.slice(0, ++i);
                        // Auto-scroll the chatbot to bottom
                        const chatScroll = document.querySelector('#aiko-chatbot > div');
                        if (chatScroll) chatScroll.scrollTop = chatScroll.scrollHeight;
                    } else {
                        clearInterval(twTimer);
                    }
                }, msPerChar);
            }

            // ── 4. Wait for audio element + its duration metadata ─────────
            function waitForAudioAndType() {
                const audioEl = document.querySelector('#aiko-audio audio');

                if (!audioEl) {
                    // Audio element not in DOM yet — poll briefly
                    setTimeout(waitForAudioAndType, 100);
                    return;
                }

                // Sanity-checked duration: must be finite, positive, and
                // under 10 minutes — guards against Infinity/NaN from
                // certain streamed/short audio files.
                function isUsableDuration(d) {
                    return Number.isFinite(d) && d > 0 && d < 600;
                }

                function start() {
                    const dur = audioEl.duration;
                    if (isUsableDuration(dur)) {
                        runTypewriter(dur);
                    } else {
                        // Fallback: estimate ~0.06s per character
                        const estimated = Math.max(2, speechText.length * 0.06);
                        runTypewriter(estimated);
                    }
                }

                if (audioEl.readyState >= 1 && isUsableDuration(audioEl.duration)) {
                    start();
                } else {
                    // Wait for metadata, but also set a fallback timeout
                    const onMeta = () => {
                        audioEl.removeEventListener('loadedmetadata', onMeta);
                        start();
                    };
                    audioEl.addEventListener('loadedmetadata', onMeta);
                    // Safety net: if metadata never fires (e.g. no audio), start anyway
                    setTimeout(() => {
                        audioEl.removeEventListener('loadedmetadata', onMeta);
                        if (isUsableDuration(audioEl.duration)) {
                            start();
                        } else {
                            runTypewriter(Math.max(2, speechText.length * 0.06));
                        }
                    }, 600);
                }
            }

            waitForAudioAndType();
        }
        """
    )

    demo.queue()

# ─────────────────────────────────────────────
# LAUNCH
# ─────────────────────────────────────────────
allowed_paths = [
    str(Path("/tmp/aiko_tts")),
    str(VRM_PATH.parent),
]

demo.launch(
    server_name="0.0.0.0",
    server_port=7860,
    ssr_mode=False,
    share=False,
    allowed_paths=allowed_paths,
    css=AIKO_CSS,
)