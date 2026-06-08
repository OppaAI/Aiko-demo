from dotenv import load_dotenv
load_dotenv()

import gradio as gr
from core.wakeup import AikoWakeup

result = AikoWakeup(text_mode=True).boot(
    on_loading=lambda k: print(f"[boot] loading: {k}"),
    on_done   =lambda k: print(f"[boot]    done: {k}"),
    on_skip   =lambda k: print(f"[boot]    skip: {k}"),
)
think    = result.think
memorize = result.memorize


def chat(message, history):
    tokens = []
    def _cb(token):
        if token.startswith("__SEARCHING__:"):
            query = token.split(":", 1)[1].strip()
            tokens.append(f"\n🔍 Searching: *{query}*\n")
        else:
            tokens.append(token)
    think.chat(message, token_callback=_cb)
    return "".join(tokens)


# ── web speech api injection ───────────────────────────────────────────────────
# Injected via gr.HTML — hooks into Gradio's existing chatbot and textbox.
# TTS: watches for new assistant messages, speaks them automatically.
# ASR: mic button (fixed position on body) captures speech, injects transcript.

_SPEECH_JS = """
<script>
(function () {
    // ── config ────────────────────────────────────────────────────────────────
    const TTS_RATE   = 1.05;
    const TTS_PITCH  = 1.1;
    const TTS_LANG   = 'en-US';
    const ASR_LANG   = 'en-US';
    // ── state ─────────────────────────────────────────────────────────────────
    let ttsEnabled  = true;
    let lastSpoken  = '';
    let recognition = null;
    let isListening = false;
    // ── wait for gradio to mount ──────────────────────────────────────────────
    function waitFor(selector, cb, interval = 200, maxTries = 50) {
        let tries = 0;
        const id = setInterval(() => {
            const el = document.querySelector(selector);
            if (el) { clearInterval(id); cb(el); }
            if (++tries >= maxTries) clearInterval(id);
        }, interval);
    }
    // ── TTS ───────────────────────────────────────────────────────────────────
    function stripMarkdown(text) {
        return text
            .replace(/🔍 Searching:.*/g, '')   // skip search indicators
            .replace(/\*\*(.*?)\*\*/g, '$1')
            .replace(/\*(.*?)\*/g, '$1')
            .replace(/`{1,3}[^`]*`{1,3}/g, '')
            .replace(/#{1,6}\s/g, '')
            .replace(/\n+/g, ' ')
            .trim();
    }
    function speak(text) {
        if (!ttsEnabled || !text) return;
        const clean = stripMarkdown(text);
        if (!clean || clean === lastSpoken) return;
        lastSpoken = clean;
        window.speechSynthesis.cancel();
        const utt = new SpeechSynthesisUtterance(clean);
        utt.lang  = TTS_LANG;
        utt.rate  = TTS_RATE;
        utt.pitch = TTS_PITCH;
        // prefer a female voice if available
        const voices = window.speechSynthesis.getVoices();
        const female = voices.find(v =>
            v.lang.startsWith('en') && /female|woman|girl/i.test(v.name)
        ) || voices.find(v => v.lang.startsWith('en'));
        if (female) utt.voice = female;
        window.speechSynthesis.speak(utt);
    }
    // observe chatbot for new assistant messages
    function watchChatbot(chatbot) {
        const observer = new MutationObserver(() => {
            // last assistant bubble — Gradio renders as .bot or [data-testid="bot"]
            const bubbles = chatbot.querySelectorAll('.message.bot, [data-testid="bot"] .md');
            if (!bubbles.length) return;
            const last = bubbles[bubbles.length - 1];
            const text = last.innerText || last.textContent || '';
            speak(text);
        });
        observer.observe(chatbot, { childList: true, subtree: true });
    }
    // ── ASR ───────────────────────────────────────────────────────────────────
    // Fixed-position button appended to body — immune to Gradio re-renders
    // that tear down and rebuild the textarea wrapper.
    function buildMicButton() {
        const btn = document.createElement('button');
        btn.id        = 'aiko-mic-btn';
        btn.innerHTML = '🎤';
        btn.title     = 'Click to speak';
        Object.assign(btn.style, {
            position:       'fixed',
            bottom:         '22px',
            right:          '60px',
            zIndex:         '9999',
            background:     'rgba(30,30,30,0.85)',
            border:         '1.5px solid #888',
            borderRadius:   '50%',
            width:          '38px',
            height:         '38px',
            fontSize:       '18px',
            cursor:         'pointer',
            transition:     'background 0.2s',
            display:        'flex',
            alignItems:     'center',
            justifyContent: 'center',
            boxShadow:      '0 2px 8px rgba(0,0,0,0.4)',
        });
        document.body.appendChild(btn);

        const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRec) {
            btn.title         = 'Speech recognition not supported in this browser';
            btn.style.opacity = '0.4';
            btn.style.cursor  = 'not-allowed';
            return;
        }

        recognition = new SpeechRec();
        recognition.lang            = ASR_LANG;
        recognition.interimResults  = false;
        recognition.maxAlternatives = 1;

        recognition.onresult = (e) => {
            const transcript = e.results[0][0].transcript.trim();
            if (!transcript) return;

            // Find the active Gradio textarea
            const inputEl =
                document.querySelector('.gradio-container textarea') ||
                document.querySelector('textarea');
            if (!inputEl) return;

            // Set value via native setter so Svelte/React picks up the change
            const proto = Object.getOwnPropertyDescriptor(
                window.HTMLTextAreaElement.prototype, 'value'
            );
            proto.set.call(inputEl, transcript);
            inputEl.dispatchEvent(new Event('input', { bubbles: true }));

            // Auto-submit after short delay
            setTimeout(() => {
                const submitBtn =
                    document.querySelector('button.submit') ||
                    document.querySelector('#component-submit-btn') ||
                    document.querySelector('[data-testid="submit-btn"]') ||
                    [...document.querySelectorAll('button')].find(
                        b => b.getAttribute('aria-label') === 'Submit' ||
                             b.textContent.trim() === '↵'             ||
                             b.textContent.trim() === 'Submit'
                    );
                if (submitBtn) submitBtn.click();
            }, 200);
        };

        recognition.onstart = () => {
            isListening          = true;
            btn.innerHTML        = '🔴';
            btn.style.background = 'rgba(255,50,50,0.25)';
            window.speechSynthesis.cancel(); // barge-in
        };
        recognition.onend = () => {
            isListening          = false;
            btn.innerHTML        = '🎤';
            btn.style.background = 'rgba(30,30,30,0.85)';
        };
        recognition.onerror = (e) => {
            console.warn('[aiko-asr] error:', e.error);
            isListening          = false;
            btn.innerHTML        = '🎤';
            btn.style.background = 'rgba(30,30,30,0.85)';
        };

        btn.addEventListener('click', () => {
            if (isListening) {
                recognition.stop();
            } else {
                try { recognition.start(); } catch(e) { console.warn(e); }
            }
        });
    }
    // ── TTS toggle button ─────────────────────────────────────────────────────
    function buildTTSToggle() {
        const btn = document.createElement('button');
        btn.id        = 'aiko-tts-btn';
        btn.innerHTML = '🔊';
        btn.title     = 'Toggle voice';
        Object.assign(btn.style, {
            position:     'fixed',
            bottom:       '22px',
            right:        '12px',
            zIndex:       '9999',
            background:   'rgba(30,30,30,0.85)',
            border:       '1.5px solid #888',
            borderRadius: '50%',
            width:        '38px',
            height:       '38px',
            fontSize:     '18px',
            cursor:       'pointer',
            boxShadow:    '0 2px 8px rgba(0,0,0,0.4)',
        });
        btn.addEventListener('click', () => {
            ttsEnabled    = !ttsEnabled;
            btn.innerHTML = ttsEnabled ? '🔊' : '🔇';
            if (!ttsEnabled) window.speechSynthesis.cancel();
        });
        document.body.appendChild(btn);
    }
    // ── init ──────────────────────────────────────────────────────────────────
    window.addEventListener('load', () => {
        // voices load async in some browsers
        if (window.speechSynthesis.onvoiceschanged !== undefined) {
            window.speechSynthesis.onvoiceschanged = () => {};
        }
        buildTTSToggle();
        buildMicButton();  // no longer needs waitFor — appended to body directly
        waitFor('.chatbot, [data-testid="chatbot"]', (chatbot) => {
            watchChatbot(chatbot);
        });
    });
})();
</script>
"""

# ── gradio ui ─────────────────────────────────────────────────────────────────

with gr.Blocks(title="Aiko-chan 🌸") as demo:
    gr.HTML(_SPEECH_JS)                          # inject speech API
    gr.ChatInterface(
        fn=chat,
        title="Aiko-chan 🌸",
        chatbot=gr.Chatbot(elem_id="aiko-chatbot"),
    )

demo.launch(server_name="0.0.0.0")
