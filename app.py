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
    """Remove search notes, tool tags, think blocks, markdown, and non-speech symbols before TTS."""
    # Remove search/tool annotations
    text = re.sub(r"\n?🔍 Searching: \*.*?\*\n?", "", text)
    text = re.sub(r"\n?🔧 .*?\n?", "", text)
    # Remove think blocks
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    # Remove markdown formatting (bold, italic, code, headers, blockquotes, hr)
    text = re.sub(r"#{1,6}\s+", "", text)          # headings
    text = re.sub(r"\*{1,3}(.*?)\*{1,3}", r"\1", text)  # bold/italic
    text = re.sub(r"_{1,2}(.*?)_{1,2}", r"\1", text)    # underscore bold/italic
    text = re.sub(r"`{1,3}.*?`{1,3}", "", text, flags=re.DOTALL)  # inline/block code
    text = re.sub(r"^\s*[-*>|]\s+", "", text, flags=re.MULTILINE)  # bullets, blockquotes, table pipes
    text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.MULTILINE)   # numbered lists
    text = re.sub(r"^-{3,}$", "", text, flags=re.MULTILINE)        # horizontal rules
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)           # markdown links → keep label
    # Remove all emoji and non-speech symbols, keep only:
    #   letters, digits, whitespace, and: , . ! ? ' " : ; - ( ) & @
    text = re.sub(
        r"[^\w\s,\.!\?'\"\:\;\-\(\)\&\@]",
        "",
        text,
        flags=re.UNICODE,
    )
    # \w keeps unicode letters/digits/underscore; strip lone underscores left behind
    text = re.sub(r"(?<!\w)_+(?!\w)", "", text)
    # Collapse multiple spaces/newlines
    text = re.sub(r"\n{2,}", "\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


# ─────────────────────────────────────────────
# CORE RESPONSE  (full text → TTS → reveal)
# ─────────────────────────────────────────────

def _get_response(message: str, history: list):
    """
    1. Show user message + thinking cursor immediately.
    2. Run LLM to full completion (no streaming to UI).
    3. Synthesize the complete response as one TTS pass.
    4. Write the FINAL spoken text into `history` (so Gradio's own render
       is already correct/persistent), and ALSO emit a TYPEWRITE signal so
       the JS can play a cosmetic reveal animation in sync with the audio
       and hand off lip-sync data to the VRM iframe.

    Voice + text are returned in the SAME yield, so they appear together,
    and the text never disappears on the next turn (it's baked into
    `history`, not living only inside a JS-controlled DOM node).

    History format: list of {"role": ..., "content": ...} dicts — Gradio 6.x
    messages format (tuple format removed in 6.x).
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
    notes_prefix = "\n".join(search_notes) + "\n\n" if search_notes else ""
    display_text = notes_prefix + speech_text

    # ── Stage 3: write the FINAL text into history (persistent, correct) ─────
    history[-1] = {"role": "assistant", "content": display_text}

    # Signal carries (emotion, notes_prefix, speech_text) for the JS
    # reveal animation / VRM lip-sync layer. The chatbot text itself is
    # already final via `history` above — this signal is purely for
    # animation + lip-sync, never the source of truth for the text.
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
    title="AI Waifu and Companion: Aiko-chan 🌸",
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

    # ── Lip-sync / reveal-animation bridge ────────────────────────────────────
    # The chatbot text is ALREADY correct and persistent (written into
    # `history` in `_get_response`, in the SAME yield as the audio). This
    # handler is now purely an animation/lip-sync layer:
    #   1. Stash speech text + emotion on `window` for the VRM iframe and
    #      post a message to it immediately so it can drive viseme/mouth
    #      shapes timed against the <audio> element (lip-sync hook).
    #   2. Play a cosmetic "reveal" animation (CSS clip-path) over the
    #      already-rendered final text, synced to audio duration — never
    #      rewriting the DOM's text content, so nothing can be lost or
    #      desync on the next turn.
    #
    # Signal format: TYPEWRITE:<emotion>|<notes_prefix>|<speech_text>
    tts_text.change(
        None,
        inputs=[tts_text],
        js="""
        (rawSignal) => {
            if (!rawSignal || !rawSignal.startsWith('TYPEWRITE:')) return;

            const rest        = rawSignal.slice('TYPEWRITE:'.length);
            const firstPipe   = rest.indexOf('|');
            const secondPipe  = rest.indexOf('|', firstPipe + 1);
            const emotion     = rest.slice(0, firstPipe);
            const notesPrefix = rest.slice(firstPipe + 1, secondPipe);
            const speechText  = rest.slice(secondPipe + 1);

            // ── 1. VRM handoff ─────────────────────────────────────────
            const iframe = document.querySelector('#aiko-vrm-frame');
            if (iframe?.contentWindow) {
                iframe.contentWindow.postMessage(
                    JSON.stringify({ expression: emotion, ttsText: speechText, notesPrefix }), '*'
                );
            }
            window._aikoLatestTtsText = speechText;
            window._aikoLatestEmotion = emotion;

            // ── 2. Character-by-character typewriter, inside the bubble ─
            function getBubbleTextNode() {
                // Try increasingly broad selectors — return the deepest text container
                const selectors = [
                    '#aiko-chatbot [data-testid="bot"] .prose p',
                    '#aiko-chatbot [data-testid="bot"] .prose',
                    '#aiko-chatbot [data-testid="bot"] .message-content',
                    '#aiko-chatbot [data-testid="bot"]',
                ];
                for (const sel of selectors) {
                    const all = document.querySelectorAll(sel);
                    if (all.length) return all[all.length - 1];
                }
                return null;
            }

            function isUsableDuration(d) {
                return Number.isFinite(d) && d > 0 && d < 600;
            }

            function runTypewriter(audioDuration) {
                // Poll until Gradio has rendered the final bubble
                // (it may not exist yet when tts_text fires)
                let attempts = 0;
                function tryStart() {
                    const el = getBubbleTextNode();
                    // Keep trying until the bubble shows something other than ▋
                    if (!el || el.textContent.trim() === '▋' || el.textContent.trim() === '') {
                        if (++attempts < 40) { setTimeout(tryStart, 50); return; }
                    }

                    // Full display text (notes + speech)
                    const fullText = (notesPrefix ? notesPrefix + '\\n\\n' : '') + speechText;

                    // Immediately blank the bubble — prevents the flash of full text
                    el.textContent = '';

                    const totalChars = fullText.length;
                    // Aim to finish at 95 % of audio duration; floor at 16 ms/char
                    const totalMs    = audioDuration * 1000 * 0.95;
                    const perChar    = Math.max(16, totalMs / totalChars);

                    let i = 0;
                    // Use a cursor character while typing
                    function tick() {
                        if (i <= totalChars) {
                            el.textContent = fullText.slice(0, i) + (i < totalChars ? '▋' : '');
                            i++;
                            setTimeout(tick, perChar);
                        } else {
                            // Ensure exact final text (no cursor)
                            el.textContent = fullText;
                            // Scroll to bottom
                            const chatbot = document.querySelector('#aiko-chatbot');
                            if (chatbot) chatbot.scrollTop = chatbot.scrollHeight;
                        }
                    }

                    // Scroll to bottom before starting
                    const chatbot = document.querySelector('#aiko-chatbot');
                    if (chatbot) chatbot.scrollTop = chatbot.scrollHeight;

                    tick();
                }
                tryStart();
            }

            function waitForAudioAndStart() {
                const audioEl = document.querySelector('#aiko-audio audio');
                if (!audioEl) { setTimeout(waitForAudioAndStart, 80); return; }

                function go() {
                    const dur = audioEl.duration;
                    const estimated = Math.max(3, speechText.length * 0.055);
                    runTypewriter(isUsableDuration(dur) ? dur : estimated);
                }

                if (audioEl.readyState >= 1 && isUsableDuration(audioEl.duration)) {
                    go();
                } else {
                    const onMeta = () => { audioEl.removeEventListener('loadedmetadata', onMeta); go(); };
                    audioEl.addEventListener('loadedmetadata', onMeta);
                    setTimeout(() => { audioEl.removeEventListener('loadedmetadata', onMeta); go(); }, 600);
                }
            }

            // Small delay so Gradio's second yield has time to render the bubble
            setTimeout(waitForAudioAndStart, 60);
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