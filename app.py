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
def _strip_emoji(text: str) -> str:
    """Remove emoji and any immediately following colon, keep all else."""
    # Remove emoji + optional trailing colon+space
    text = re.sub(
        r"[\U00010000-\U0010FFFF"
        r"\U00002600-\U000027BF"
        r"\U0001F000-\U0001FFFF"
        r"\U00002300-\U000023FF"
        r"\U00002B00-\U00002BFF"
        r"\U0001FA00-\U0001FFFF"
        r"]:?",
        "",
        text,
        flags=re.UNICODE,
    )
    return text


def _strip_for_speech(text: str) -> str:
    """Aggressive clean for TTS — removes markdown, symbols, emoji."""
    # Remove search/tool annotations
    text = re.sub(r"\n?🔍 Searching: \*.*?\*\n?", "", text)
    text = re.sub(r"\n?🔧 .*?\n?", "", text)
    # Remove think blocks
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    # Strip markdown formatting
    text = re.sub(r"#{1,6}\s+", "", text)
    text = re.sub(r"\*{1,3}(.*?)\*{1,3}", r"\1", text)
    text = re.sub(r"_{1,2}(.*?)_{1,2}", r"\1", text)
    text = re.sub(r"`{1,3}.*?`{1,3}", "", text, flags=re.DOTALL)
    text = re.sub(r"^\s*[-*>|]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^-{3,}$", "", text, flags=re.MULTILINE)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    # Keep only speech-friendly characters
    text = re.sub(r"[^\w\s,\.!\?'\"\:\;\-\(\)\&\@]", "", text, flags=re.UNICODE)
    text = re.sub(r"(?<!\w)_+(?!\w)", "", text)
    # Collapse whitespace
    text = re.sub(r"\n{2,}", "\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def _detect_emoji_emotion(text: str) -> str | None:
    """Map emoji in response to VRM expression names."""
    EMOJI_MAP = {
        "😊": "happy", "😄": "happy", "😁": "happy", "🥰": "happy",
        "😍": "happy", "🤗": "happy", "✨": "happy", "💕": "happy",
        "💖": "happy", "🌸": "happy", "😆": "happy", "😸": "happy",
        "😢": "sad",   "😭": "sad",   "😔": "sad",   "💔": "sad",
        "😞": "sad",   "🥺": "sad",   "😿": "sad",
        "😠": "angry", "😤": "angry", "🤬": "angry", "💢": "angry",
        "😾": "angry", "👿": "angry",
        "😮": "surprised", "😲": "surprised", "🤯": "surprised",
        "😱": "surprised", "👀": "surprised",
        "😌": "relaxed", "🙂": "relaxed",
        "😶": "neutral", "🤔": "neutral", "😏": "neutral",
    }
    for emoji, expr in EMOJI_MAP.items():
        if emoji in text:
            return expr
    return None


# ─────────────────────────────────────────────
# CORE RESPONSE
# ─────────────────────────────────────────────
def _get_response(message: str, history: list):
    history = list(history) + [
        {"role": "user",      "content": message},
        {"role": "assistant", "content": "▋"},
    ]
    yield history, None, None

    # ── Stage 1: full LLM completion ─────────────────────────────────────────
    full_text = ""
    tool_lines: list[str] = []

    def _cb(token: str):
        nonlocal full_text
        if token.startswith("__SEARCHING__:"):
            tool_lines.append("🌐 Searching internet...")
        elif token.startswith("__TOOL__:"):
            tool_lines.append("⚙️ Executing skill...")
        else:
            full_text += token

    think.chat(message, token_callback=_cb)

    # ── Stage 2: TTS on clean speech text ────────────────────────────────────
    speech_text = _strip_for_speech(full_text)
    if speech_text:
        audio_path, emotion = speak_to_file(speech_text)
    else:
        audio_path, emotion = None, "neutral"

    # Emoji overrides TTS-detected emotion
    emoji_emotion = _detect_emoji_emotion(full_text)
    final_emotion = emoji_emotion or emotion

    # ── Stage 3: build display text ────────────────────────────────────────
    # Tool/search lines on their own line(s), response starts on the next line.
    notes_prefix = ("\n".join(tool_lines) + "\n\n") if tool_lines else ""
    response_text = _strip_emoji(full_text)
    display_text = notes_prefix + response_text

    history[-1] = {"role": "assistant", "content": display_text}

    # Keep the original 2-part signal format — JS typewriter unchanged.
    # fullText for the typewriter is just the response (no notes),
    # so notes don't get animated.
    signal = f"TYPEWRITE:{final_emotion}||{notes_prefix}||{response_text}"
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
            yield h, tts, audio, ""
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
# LOGIN HANDLER
# ─────────────────────────────────────────────
def _check_login(profile: OAuthProfile | None):
    if profile is None:
        return "Guest", gr.update(visible=True), gr.update(visible=False)

    user_id = profile.username or "Guest"
    soul = build_soul_prompt(user_id)

    if hasattr(think, "set_system_prompt"):
        think.set_system_prompt(soul)
    elif hasattr(think, "system_prompt"):
        think.system_prompt = soul

    return user_id, gr.update(visible=False), gr.update(visible=True)


# ─────────────────────────────────────────────
# UI
# ─────────────────────────────────────────────
with gr.Blocks(title="🌸 AI Waifu and Companion Aiko-chan") as demo:

    user_id_state = gr.State(value="Guest")

    # ── Login popup overlay ──────────────────────────────────────
    with gr.Column(elem_id="aiko-login-overlay") as login_overlay:
        with gr.Column(elem_id="aiko-login-card"):
            gr.HTML("""
                <h1>🌸 AI Waifu and Companion Aiko-chan</h1>
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

    with gr.Column(elem_id="aiko-info-overlay", visible=False) as info_overlay:
        with gr.Column(elem_id="aiko-info-card"):
            gr.HTML("""
                <h2>🌸 About Aiko-chan</h2>
                <p>Aiko is your AI companion — chat, ask questions, or just talk.</p>
                <p>She's got her own personality, moods, and opinions, and she remembers context as you talk. Sometimes sweet, sometimes a little savage — never boring. And she'll give you an actual answer whenever she feels like it.</p>
                <p><strong>Try asking:</strong></p>
                <ul>
                    <li>"What's the score of [game]?" → triggers live sports lookup</li>
                    <li>"What's the weather in [city]?" → triggers weather tool</li>
                    <li>"Search the web for..." → triggers web search</li>
                    <li>"What's [crypto] price?" → triggers price lookup</li>
                </ul>
                <p><strong>Tips:</strong></p>
                <ul>
                    <li>Use 🎙️ to speak instead of typing</li>
                    <li>Aiko reacts emotionally — try different tones!</li>
                </ul>
            """)
            info_ok_btn = gr.Button("Got it!", elem_id="aiko-info-ok-btn")

    with gr.Column(elem_id="aiko-shell"):

        gr.HTML("<div id='aiko-title'>🌸 AI Waifu and Companion Aiko-chan</div>")

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
                        visible=False,
                    )

    # ─────────────────────────────────────────────
    # EVENTS
    # ─────────────────────────────────────────────
    demo.load(
        _check_login,
        inputs=None,
        outputs=[user_id_state, login_overlay, info_overlay],
    )

    info_ok_btn.click(
        lambda: gr.update(visible=False),
        inputs=None,
        outputs=info_overlay,
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

    # ── Typewriter / lip-sync bridge ──────────────────────────────────────────
    # Signal format: TYPEWRITE:<emotion>||<display_text>
    # (double-pipe so notes_prefix slot is empty — display_text already contains it)
    tts_text.change(
        None,
        inputs=[tts_text],
        js="""
        (rawSignal) => {
            if (!rawSignal || !rawSignal.startsWith('TYPEWRITE:')) return;

            const rest    = rawSignal.slice('TYPEWRITE:'.length);
            const parts   = rest.split('||');
            const emotion = parts[0];
            const notesPrefix = parts[1] || '';
            const fullText    = parts[2] || '';

            // ── 1. VRM handoff ──────────────────────────────────────
            const iframe = document.querySelector('#aiko-vrm-frame');
            if (iframe?.contentWindow) {
                iframe.contentWindow.postMessage(
                    JSON.stringify({ expression: emotion, ttsText: fullText }), '*'
                );
            }
            window._aikoLatestTtsText = fullText;
            window._aikoLatestEmotion = emotion;

            // ── 2. Helpers ──────────────────────────────────────────
            function getBubbleEl() {
                const allBubbles = document.querySelectorAll('#aiko-chatbot [data-testid="bot"]');
                if (!allBubbles.length) return null;
                const last = allBubbles[allBubbles.length - 1];
                return (
                    last.querySelector('.prose') ||
                    last.querySelector('.message-content') ||
                    last
                );
            }

            function wipeEl(el) {
                while (el.firstChild) el.removeChild(el.firstChild);
                el.textContent = '';
            }

            function isUsableDuration(d) {
                return Number.isFinite(d) && d > 0 && d < 600;
            }

            // ── 3. Blank watcher — fires immediately via rAF ────────
            // Catches the bubble the instant ▋ (yield 1) or the full
            // text (yield 2) appears, wipes it, and holds it blank via
            // MutationObserver until the typewriter takes over.
            let blanked       = false;
            let targetEl      = null;
            let typingStarted = false;

            function blankWatcher() {
                const el = getBubbleEl();
                if (!el) { requestAnimationFrame(blankWatcher); return; }

                if (el.textContent.trim() !== '') {
                    targetEl = el;
                    wipeEl(el);
                    if (notesPrefix) {
                        const notesSpan = document.createElement('div');
                        notesSpan.textContent = notesPrefix.trim();
                        notesSpan.style.opacity = '0.7';
                        notesSpan.style.fontSize = '0.9em';
                        el.appendChild(notesSpan);
                    }
                    const responseSpan = document.createElement('span');
                    el.appendChild(responseSpan);
                    targetEl._responseSpan = responseSpan;
                    blanked = true;

                    const obs = new MutationObserver(() => {
                        if (!typingStarted) wipeEl(el);
                    });
                    obs.observe(el, { childList: true, subtree: true, characterData: true });
                    window._aikoBlankObs = obs;
                } else {
                    requestAnimationFrame(blankWatcher);
                }
            }
            blankWatcher();

            // ── 4. Typewriter — starts as soon as bubble is blanked ─
            function startTypewriter() {
                if (!blanked || !targetEl) { setTimeout(startTypewriter, 300); return; }

                typingStarted = true;

                if (window._aikoBlankObs) {
                    window._aikoBlankObs.disconnect();
                    window._aikoBlankObs = null;
                }

                const totalChars = fullText.length;
                // Estimate pace from char count (stripped of markdown for timing)
                const cleanLen   = fullText.replace(/[*_#`]/g, '').length;
                let audioDur = Math.max(3, cleanLen * 0.055);
                let totalMs      = audioDur * 1000;
                let perChar      = totalMs / Math.max(1, totalChars);

                // Use real audio duration if already available
                const audioEl = document.querySelector('#aiko-audio audio');
                if (audioEl && isUsableDuration(audioEl.duration)) {
                    audioDur = audioEl.duration;
                    totalMs  = audioDur * 1000;
                    perChar  = totalMs / Math.max(1, totalChars);
                }

                let i         = 0;
                let startTime = performance.now();
                function tick() {
                    if (i >= totalChars) {
                        targetEl.textContent = fullText;
                        const cb = document.querySelector('#aiko-chatbot');
                        if (cb) cb.scrollTop = cb.scrollHeight;
                        return;
                    }
                    const elapsed  = performance.now() - startTime;
                    const shouldBe = Math.floor((elapsed / totalMs) * totalChars);
                    i = Math.min(Math.max(shouldBe, 0), totalChars);

                    targetEl.textContent = i < totalChars
                        ? fullText.slice(0, i) + '▋'
                        : fullText;

                    const cb = document.querySelector('#aiko-chatbot');
                    if (cb) cb.scrollTop = cb.scrollHeight;

                    setTimeout(tick, perChar);
                }

                // Resync pace when real audio duration arrives
                function onAudioReady(el) {
                    if (!isUsableDuration(el.duration)) return;
                    const elapsed   = performance.now() - startTime;
                    const charsLeft = Math.max(1, totalChars - i);
                    const timeLeft  = Math.max(100, el.duration * 1000 - elapsed);
                    perChar = timeLeft / charsLeft;
                    totalMs = el.duration * 1000;
                }

                if (audioEl) {
                    if (isUsableDuration(audioEl.duration)) {
                        onAudioReady(audioEl);
                    } else {
                        audioEl.addEventListener('loadedmetadata', function h() {
                            audioEl.removeEventListener('loadedmetadata', h);
                            onAudioReady(audioEl);
                        });
                    }
                } else {
                    (function pollAudio() {
                        const a = document.querySelector('#aiko-audio audio');
                        if (!a) { setTimeout(pollAudio, 80); return; }
                        if (isUsableDuration(a.duration)) {
                            onAudioReady(a);
                        } else {
                            a.addEventListener('loadedmetadata', function h() {
                                a.removeEventListener('loadedmetadata', h);
                                onAudioReady(a);
                            });
                        }
                    })();
                }

                tick();
            }

            startTypewriter();
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