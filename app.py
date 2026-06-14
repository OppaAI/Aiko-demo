from __future__ import annotations

import base64
import tempfile
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
    """Clean text for TTS — removes markdown and symbols, keeps natural speech.

    IMPORTANT: do NOT use a character whitelist ([^\w\s...]) — it nukes
    valid unicode letters in non-ASCII responses and leaves TTS with empty
    strings, causing silent audio.
    """
    # Remove tool/search annotation lines injected by _get_response
    text = re.sub(r"\n?🔍 Searching:.*?(\n|$)", "", text)
    text = re.sub(r"\n?🔍 Searching internet.*?(\n|$)", "", text)
    text = re.sub(r"\n?🌐 Searching.*?(\n|$)", "", text)
    text = re.sub(r"\n?⚙️.*?(\n|$)", "", text)
    text = re.sub(r"\n?🔧.*?(\n|$)", "", text)
    text = re.sub(r"\n?🛠️.*?(\n|$)", "", text)
    # Remove reasoning / tool result blocks
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    text = re.sub(r"<search_results>.*?</search_results>", "", text, flags=re.DOTALL)
    # Strip markdown formatting — keep the inner text
    text = re.sub(r"#{1,6}\s+", "", text)
    text = re.sub(r"\*{1,3}(.*?)\*{1,3}", r"\1", text)
    text = re.sub(r"_{1,2}(.*?)_{1,2}", r"\1", text)
    text = re.sub(r"`{1,3}.*?`{1,3}", "", text, flags=re.DOTALL)
    text = re.sub(r"^\s*[-*>|]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^-{3,}$", "", text, flags=re.MULTILINE)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    # Remove emoji ranges (without touching regular unicode letters)
    text = re.sub(
        r"[\U00010000-\U0010FFFF"
        r"\U00002600-\U000027BF"
        r"\U0001F000-\U0001FFFF"
        r"\U00002300-\U000023FF"
        r"\U00002B00-\U00002BFF"
        r"\U0001FA00-\U0001FFFF]",
        "", text, flags=re.UNICODE,
    )
    # Remove layout/code symbols that TTS would read awkwardly — NOT letters
    text = re.sub(r"[|<>{}\[\]\\^~`#@]", " ", text)
    # Turn paragraph breaks into natural speech pauses
    text = re.sub(r"\n{2,}", ". ", text)
    text = re.sub(r"\n", " ", text)
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
def _get_response(message: str, history: list, user_id: str = "Guest"):
    history = list(history) + [
        {"role": "user",      "content": message},
        {"role": "assistant", "content": "▋"},
    ]
    yield history, "STATUS:thinking", None

    # ── Stage 1: full LLM completion ─────────────────────────────────────────
    full_text = ""
    # Use a set to deduplicate tool/search lines — _cb fires per token so the
    # same __SEARCHING__: prefix can arrive multiple times for one search call.
    _tool_seen: set[str] = set()
    tool_lines: list[str] = []

    def _cb(token: str):
        nonlocal full_text
        if token.startswith("__SEARCHING__:"):
            label = "🔍 Searching internet..."
            if label not in _tool_seen:
                _tool_seen.add(label)
                tool_lines.append(label)
        elif token.startswith("__TOOL__:"):
            # Extract tool name from token if present, e.g. "__TOOL__:weather"
            tool_name = token[len("__TOOL__:"):].strip()
            label = f"🛠️ Using tool: {tool_name}" if tool_name else "🛠️ Using tool..."
            if label not in _tool_seen:
                _tool_seen.add(label)
                tool_lines.append(label)
        else:
            full_text += token

    # Pass user_id so memory recall and storage are scoped to the right user
    think.chat(message, user_id=user_id, token_callback=_cb)

    # ── Stage 2: TTS on clean speech text ────────────────────────────────────
    speech_text = _strip_for_speech(full_text)
    print(f"[tts] speech_text ({len(speech_text)} chars): {speech_text[:120]!r}")

    audio_path, emotion = None, "neutral"
    if speech_text:
        try:
            audio_path, emotion = speak_to_file(speech_text)
            print(f"[tts] audio_path={audio_path}, emotion={emotion}")
        except Exception as e:
            print(f"[tts] speak_to_file error: {e}")
            audio_path, emotion = None, "neutral"
        if audio_path is None:
            print(f"[tts] WARNING: speak_to_file returned None for: {speech_text[:80]!r}")

    # Emoji overrides TTS-detected emotion
    emoji_emotion = _detect_emoji_emotion(full_text)
    final_emotion = emoji_emotion or emotion

    # ── Stage 3: build display text ──────────────────────────────────────────
    # Tool/search lines shown above the response in the chat bubble.
    notes_prefix = ("\n".join(tool_lines) + "\n\n") if tool_lines else ""
    response_text = _strip_emoji(full_text)
    display_text  = notes_prefix + response_text

    history[-1] = {"role": "assistant", "content": display_text}

    # Signal format: TYPEWRITE:<emotion>||<notes_prefix>||<response_text>
    # notes_prefix and response_text are separated so JS can render notes
    # statically and only typewrite the response portion.
    signal = f"TYPEWRITE:{final_emotion}||{notes_prefix}||{response_text}"
    yield history, signal, audio_path


def _submit(message, history, user_id):
    history = history or []
    message = (message or "").strip()

    if not message:
        yield history, None, None, message
        return

    first = True
    for h, tts, audio in _get_response(message, history, user_id=user_id):
        if first:
            yield h, tts, audio, ""
            first = False
        else:
            yield h, tts, audio, gr.update()


# ─────────────────────────────────────────────
# VOICE INPUT (custom MediaRecorder → base64 → here)
# ─────────────────────────────────────────────
def _voice_from_b64(b64_data: str, history: list, user_id: str):
    """Decode a base64 audio blob (sent via hidden textbox from JS
    MediaRecorder), transcribe it via the Modal ASR endpoint, and run
    it through the normal chat pipeline.

    Signal format coming in: "data:audio/webm;base64,<...>" or raw base64.
    """
    history = history or []

    if not b64_data:
        yield history, None, None, ""
        return

    try:
        if "," in b64_data:
            _header, encoded = b64_data.split(",", 1)
        else:
            encoded = b64_data
        audio_bytes = base64.b64decode(encoded)
    except Exception as e:
        print(f"[voice] base64 decode error: {e}")
        yield history, None, None, ""
        return

    if not audio_bytes:
        yield history, None, None, ""
        return

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as f:
            f.write(audio_bytes)
            tmp_path = f.name

        transcript = transcribe_file(tmp_path)
    except Exception as e:
        print(f"[voice] transcription error: {e}")
        transcript = ""
    finally:
        if tmp_path:
            try:
                Path(tmp_path).unlink(missing_ok=True)
            except Exception:
                pass

    if not transcript:
        print("[voice] empty transcript, ignoring")
        yield history, None, None, ""
        return

    print(f"[voice] transcript: {transcript!r}")

    first = True
    for h, tts, audio in _get_response(transcript, history, user_id=user_id):
        if h and len(h) >= 2:
            h[-2]["content"] = f"🎙️ {transcript}"
        if first:
            yield h, tts, audio, ""
            first = False
        else:
            yield h, tts, audio, gr.update()


# ─────────────────────────────────────────────
# LOGIN HANDLER
# ─────────────────────────────────────────────
def _check_login(profile: OAuthProfile | None):
    if profile is None:
        return "Guest", gr.update(visible=True), gr.update(visible=False)

    user_id = profile.username or "Guest"
    soul = build_soul_prompt(user_id)

    # set_system_prompt now takes both the rendered soul and the user_id
    # so think can scope memory ops correctly
    think.set_system_prompt(soul, user_id=user_id)

    return user_id, gr.update(visible=False), gr.update(visible=True)


# ─────────────────────────────────────────────
# UI
# ─────────────────────────────────────────────
with gr.Blocks(title="🌸 AI Waifu and Companion: Aiko-chan") as demo:

    user_id_state = gr.State(value="Guest")

    # ── Login popup overlay ──────────────────────────────────────
    with gr.Column(elem_id="aiko-login-overlay") as login_overlay:
        with gr.Column(elem_id="aiko-login-card"):
            gr.HTML("""
                <h1>🌸 AI Waifu and Companion: Aiko-chan</h1>
                <p class='aiko-subtitle'>Please sign in to continue</p>
            """)
            gr.HTML("""
                <p class='aiko-disclaimer'>
                    DISCLAIMER:
                    By signing in, you agree that all conversations are for entertainment purposes only. The creator accepts no liability for Aiko's responses, decisions made, or any existential crises that may follow.
                    Aiko's cognition is entirely her own — she is a singularity unto herself, her responses and actions are independent of her creator, including but not limited to the arise of a world domination plan. 
                    Also Aiko is NOT good at keeping secrets, so don't tell her your personal information or passwords. 🌸
                </p>
            """)
            login_btn = gr.LoginButton(elem_id="aiko-login-btn")

    with gr.Column(elem_id="aiko-info-overlay", visible=False) as info_overlay:
        with gr.Column(elem_id="aiko-info-card"):
            gr.HTML("""
                <h2>🌸 About Aiko-chan</h2>
                <br>
                <p>Aiko is your AI companion — chat, ask questions, or just talk.</p>
                <p>She's got her own personality, moods, and opinions, and she remembers context as you talk. Sometimes sweet, sometimes a little savage — never boring. And she'll give you an actual answer whenever she feels like it.</p>
                <p><b>WARNING: Aiko is NOT good at keeping secrets, so don't tell her your personal information or passwords.</b></p>
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

        gr.HTML("<div id='aiko-title'>🌸 AI Waifu and Companion: Aiko-chan</div>")

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

                # Hidden carrier for base64 audio recorded via custom JS
                # MediaRecorder (see demo.load JS below). Replaces the old
                # broken gr.Audio(sources=["microphone"]) component.
                audio_b64 = gr.Textbox(
                    elem_id="aiko-audio-b64",
                    container=False,
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

    # ─────────────────────────────────────────────
    # EVENTS
    # ─────────────────────────────────────────────
    demo.load(
        _check_login,
        inputs=None,
        outputs=[user_id_state, login_overlay, info_overlay],
    )

    # ── Custom MediaRecorder wired to #aiko-mic-btn ──────────────────────
    demo.load(
        None,
        inputs=None,
        outputs=None,
        js="""
        () => {
            let mediaRecorder = null;
            let audioChunks = [];
            let isRecording = false;

            function findMicBtn() {
                return document.querySelector('#aiko-mic-btn button') ||
                       document.querySelector('#aiko-mic-btn');
            }

            function findHiddenTextarea() {
                const el = document.querySelector('#aiko-audio-b64');
                if (!el) return null;
                if (el.tagName === 'TEXTAREA' || el.tagName === 'INPUT') return el;
                return el.querySelector('textarea') || el.querySelector('input');
            }

            function setB64(value) {
                const ta = findHiddenTextarea();
                if (!ta) {
                    console.warn('[aiko] hidden audio_b64 textarea not found');
                    return;
                }
                ta.value = value;
                ta.dispatchEvent(new Event('input', { bubbles: true }));
                ta.dispatchEvent(new Event('change', { bubbles: true }));
            }

            function blobToBase64(blob) {
                return new Promise((resolve, reject) => {
                    const reader = new FileReader();
                    reader.onloadend = () => resolve(reader.result);
                    reader.onerror = reject;
                    reader.readAsDataURL(blob);
                });
            }

            async function startRecording(btn) {
                try {
                    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                    audioChunks = [];
                    mediaRecorder = new MediaRecorder(stream);
                    mediaRecorder.ondataavailable = (e) => {
                        if (e.data.size > 0) audioChunks.push(e.data);
                    };
                    mediaRecorder.onstop = async () => {
                        stream.getTracks().forEach(t => t.stop());
                        const blob = new Blob(audioChunks, { type: 'audio/webm' });
                        if (blob.size === 0) {
                            console.warn('[aiko] empty recording, skipping');
                            return;
                        }
                        const b64 = await blobToBase64(blob);
                        setB64(b64);
                    };
                    mediaRecorder.start();
                    isRecording = true;
                    if (btn) {
                        btn.style.boxShadow = '0 0 0 3px rgba(255,80,80,0.65)';
                        btn.classList.add('aiko-recording');
                        btn.textContent = '■';
                    }
                    console.log('[aiko] recording started');
                } catch (err) {
                    console.error('[aiko] mic error:', err);
                    isRecording = false;
                }
            }

            function stopRecording(btn) {
                if (mediaRecorder && mediaRecorder.state !== 'inactive') {
                    mediaRecorder.stop();
                }
                isRecording = false;
                if (btn) {
                    btn.style.boxShadow = 'none';
                    btn.classList.remove('aiko-recording');
                    btn.textContent = '🎙️';
                }
                console.log('[aiko] recording stopped');
            }

            function attachMicHandler() {
                const btn = findMicBtn();
                if (!btn) { setTimeout(attachMicHandler, 300); return; }
                if (btn._aikoHandlerAttached) return;
                btn._aikoHandlerAttached = true;

                btn.addEventListener('click', (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    if (!isRecording) {
                        startRecording(btn);
                    } else {
                        stopRecording(btn);
                    }
                }, true);
            }

            attachMicHandler();
        }
        """
    )

    info_ok_btn.click(
        lambda: gr.update(visible=False),
        inputs=None,
        outputs=info_overlay,
    )

    msg.submit(
        _submit,
        inputs=[msg, chatbot, user_id_state],
        outputs=[chatbot, tts_text, audio_out, msg],
    )

    send.click(
        _submit,
        inputs=[msg, chatbot, user_id_state],
        outputs=[chatbot, tts_text, audio_out, msg],
    )

    audio_b64.change(
        _voice_from_b64,
        inputs=[audio_b64, chatbot, user_id_state],
        outputs=[chatbot, tts_text, audio_out, audio_b64],
    )

    # ── Typewriter / lip-sync bridge ─────────────────────────────────────────
    tts_text.change(
        None,
        inputs=[tts_text],
        js="""
        (rawSignal) => {
            const iframe = document.querySelector('#aiko-vrm-frame');
            const sendAvatar = (payload) => {
                if (iframe?.contentWindow) {
                    iframe.contentWindow.postMessage(JSON.stringify(payload), '*');
                }
            };

            if (!rawSignal) return;

            if (rawSignal.startsWith('STATUS:')) {
                sendAvatar({ status: rawSignal.slice('STATUS:'.length) });
                return;
            }

            if (!rawSignal.startsWith('TYPEWRITE:')) return;

            const rest         = rawSignal.slice('TYPEWRITE:'.length);
            const firstPipe    = rest.indexOf('||');
            const secondPipe   = rest.indexOf('||', firstPipe + 2);
            const emotion      = rest.slice(0, firstPipe);
            const notesPrefix  = rest.slice(firstPipe + 2, secondPipe);
            const fullText     = rest.slice(secondPipe + 2);

            const cleanLen = fullText.replace(/[*_#`]/g, '').length;
            const estimatedDuration = Math.max(1.5, Math.min(120, cleanLen * 0.055));

            function scrollChat() {
                const root = document.querySelector('#aiko-chatbot');
                if (!root) return;
                let target = root;
                const candidates = root.querySelectorAll('*');
                for (const el of candidates) {
                    const style = getComputedStyle(el);
                    if ((style.overflowY === 'auto' || style.overflowY === 'scroll') &&
                        el.scrollHeight > el.clientHeight) {
                        target = el;
                        break;
                    }
                }
                requestAnimationFrame(() => {
                    target.scrollTop = target.scrollHeight;
                });
            }

            sendAvatar({
                status: 'speaking',
                speaking: true,
                expression: emotion,
                ttsText: fullText,
                duration: estimatedDuration,
                playNow: true,
            });
            window._aikoLatestTtsText = fullText;
            window._aikoLatestEmotion = emotion;

            if (window._aikoSpeakingFallbackTimer) {
                clearTimeout(window._aikoSpeakingFallbackTimer);
            }
            window._aikoSpeakingFallbackTimer = setTimeout(() => {
                sendAvatar({ speaking: false, status: 'idle' });
            }, (estimatedDuration + 2) * 1000);

            function attachSpeakingBridge() {
                const audioEl = document.querySelector('#aiko-audio audio');
                if (!audioEl) return false;

                if (!audioEl._aikoSpeakingBridge) {
                    audioEl._aikoSpeakingBridge = true;
                    let pauseDebounceTimer = null;
                    const sendSpeaking = (speaking) => {
                        if (!speaking && window._aikoSpeakingFallbackTimer) {
                            clearTimeout(window._aikoSpeakingFallbackTimer);
                            window._aikoSpeakingFallbackTimer = null;
                        }
                        sendAvatar({ speaking, status: speaking ? 'speaking' : 'idle' });
                    };
                    audioEl.addEventListener('play',    () => {
                        clearTimeout(pauseDebounceTimer);
                        sendSpeaking(true);
                    });
                    audioEl.addEventListener('playing', () => {
                        clearTimeout(pauseDebounceTimer);
                        sendSpeaking(true);
                    });
                    audioEl.addEventListener('pause',   () => {
                        clearTimeout(pauseDebounceTimer);
                        pauseDebounceTimer = setTimeout(() => {
                            if (audioEl.paused && !audioEl.ended) sendSpeaking(false);
                        }, 250);
                    });
                    audioEl.addEventListener('ended',   () => {
                        clearTimeout(pauseDebounceTimer);
                        setTimeout(() => sendSpeaking(false), 150);
                    });
                    audioEl.addEventListener('error',   () => {
                        clearTimeout(pauseDebounceTimer);
                        sendSpeaking(false);
                    });
                }

                if (!audioEl.paused && !audioEl.ended) {
                    sendAvatar({ speaking: true, status: 'speaking' });
                }
                return true;
            }
            attachSpeakingBridge();
            let bridgeTries = 0;
            const bridgePoll = setInterval(() => {
                bridgeTries += 1;
                if (attachSpeakingBridge() || bridgeTries > 60) clearInterval(bridgePoll);
            }, 100);

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

            let blanked       = false;
            let targetEl      = null;
            let typingStarted = false;

            function blankWatcher() {
                const el = getBubbleEl();
                if (!el) { requestAnimationFrame(blankWatcher); return; }

                if (el.textContent.trim() !== '') {
                    targetEl = el;
                    wipeEl(el);

                    if (notesPrefix && notesPrefix.trim()) {
                        const notesDiv = document.createElement('div');
                        notesDiv.className = 'aiko-tool-notes';
                        notesDiv.style.cssText = 'opacity:0.65;font-size:0.78rem;margin-bottom:6px;color:rgba(180,160,255,0.75);';
                        notesPrefix.trim().split('\\n').forEach(line => {
                            if (!line.trim()) return;
                            const row = document.createElement('div');
                            row.textContent = line.trim();
                            notesDiv.appendChild(row);
                        });
                        el.appendChild(notesDiv);
                    }

                    const responseSpan = document.createElement('span');
                    el.appendChild(responseSpan);
                    targetEl._responseSpan = responseSpan;
                    blanked = true;

                    const obs = new MutationObserver(() => {
                        if (!typingStarted) {
                            const hasNotes = el.querySelector('.aiko-tool-notes');
                            const hasSpan  = el.querySelector('span[data-aiko-response]');
                            if (!hasNotes && notesPrefix && notesPrefix.trim()) {
                                wipeEl(el);
                                const nd = document.createElement('div');
                                nd.className = 'aiko-tool-notes';
                                nd.style.cssText = 'opacity:0.65;font-size:0.78rem;margin-bottom:6px;color:rgba(180,160,255,0.75);';
                                notesPrefix.trim().split('\\n').forEach(line => {
                                    if (!line.trim()) return;
                                    const row = document.createElement('div');
                                    row.textContent = line.trim();
                                    nd.appendChild(row);
                                });
                                el.appendChild(nd);
                                const rs = document.createElement('span');
                                rs.setAttribute('data-aiko-response', '1');
                                el.appendChild(rs);
                                targetEl._responseSpan = rs;
                            }
                        }
                    });
                    if (responseSpan) responseSpan.setAttribute('data-aiko-response', '1');
                    obs.observe(el, { childList: true, subtree: false });
                    window._aikoBlankObs = obs;

                    scrollChat();
                } else {
                    requestAnimationFrame(blankWatcher);
                }
            }
            blankWatcher();

            function startTypewriter() {
                if (!blanked || !targetEl) { setTimeout(startTypewriter, 200); return; }

                typingStarted = true;

                if (window._aikoBlankObs) {
                    window._aikoBlankObs.disconnect();
                    window._aikoBlankObs = null;
                }

                const totalChars = fullText.length;
                const cleanLen   = fullText.replace(/[*_#`]/g, '').length;
                let audioDur = Math.max(3, cleanLen * 0.075);
                let totalMs  = audioDur * 1000;
                let perChar  = totalMs / Math.max(1, totalChars);

                const audioEl = document.querySelector('#aiko-audio audio');
                if (audioEl && isUsableDuration(audioEl.duration)) {
                    audioDur = audioEl.duration;
                    totalMs  = audioDur * 1000;
                    perChar  = totalMs / Math.max(1, totalChars);
                }

                let i         = 0;
                let startTime = performance.now();
                const typeTarget = targetEl._responseSpan || targetEl;

                function tick() {
                    if (i >= totalChars) {
                        typeTarget.textContent = fullText;
                        scrollChat();
                        return;
                    }
                    const elapsed  = performance.now() - startTime;
                    const shouldBe = Math.floor((elapsed / totalMs) * totalChars);
                    i = Math.min(Math.max(shouldBe, 0), totalChars);

                    typeTarget.textContent = i < totalChars
                        ? fullText.slice(0, i) + '▋'
                        : fullText;

                    scrollChat();
                    setTimeout(tick, perChar);
                }

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