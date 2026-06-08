SPEECH_JS = """
<script>
(function () {
    'use strict';
    const TTS_RATE = 1.05, TTS_PITCH = 1.1, TTS_LANG = 'en-US', ASR_LANG = 'en-US';
    let ttsEnabled = true, lastSpoken = '', recognition = null, isListening = false;
    let voicesLoaded = false;

    // ── utils ─────────────────────────────────────────────────────────────────
    function waitFor(selector, cb, interval = 300, maxTries = 60) {
        let tries = 0;
        const id = setInterval(() => {
            const el = document.querySelector(selector);
            if (el) { clearInterval(id); cb(el); }
            if (++tries >= maxTries) clearInterval(id);
        }, interval);
    }

    function stripMarkdown(text) {
        return text
            .replace(/🔍\\s*Searching:.*/g, '')
            .replace(/\\*\\*(.*?)\\*\\*/g, '$1')
            .replace(/\\*(.*?)\\*/g, '$1')
            .replace(/`{1,3}[^`]*`{1,3}/g, '')
            .replace(/#{1,6}\\s/g, '')
            .replace(/\\n+/g, ' ')
            .trim();
    }

    // ── TTS ───────────────────────────────────────────────────────────────────
    function loadVoices() {
        return window.speechSynthesis.getVoices();
    }

    function getBestVoice() {
        const voices = loadVoices();
        if (!voices.length) return null;
        // Prefer a natural-sounding English female voice
        const preferred = [
            v => v.lang === 'en-US' && /Google US English/i.test(v.name),
            v => v.lang === 'en-US' && /Samantha/i.test(v.name),
            v => v.lang === 'en-US' && /Victoria/i.test(v.name),
            v => v.lang === 'en-US' && /female|woman|girl/i.test(v.name),
            v => v.lang === 'en-US' && /en-US/i.test(v.lang),
            v => v.lang.startsWith('en'),
        ];
        for (const pred of preferred) {
            const v = voices.find(pred);
            if (v) return v;
        }
        return voices[0];
    }

    function speak(text) {
        if (!ttsEnabled || !text) return;
        const clean = stripMarkdown(text);
        if (!clean || clean === lastSpoken) return;
        lastSpoken = clean;

        window.speechSynthesis.cancel();

        // Some browsers need a small delay after cancel
        setTimeout(() => {
            const utt = new SpeechSynthesisUtterance(clean);
            utt.lang = TTS_LANG;
            utt.rate = TTS_RATE;
            utt.pitch = TTS_PITCH;
            const voice = getBestVoice();
            if (voice) utt.voice = voice;
            window.speechSynthesis.speak(utt);
        }, 50);
    }

    // ── Chat observer ─────────────────────────────────────────────────────────
    function watchChatbot(chatbot) {
        // Watch for new bot messages appearing
        const observer = new MutationObserver((mutations) => {
            // Find the last bot bubble
            const bubbles = chatbot.querySelectorAll('.message.bot, [data-testid="bot"], .bot-message, .message-wrap.bot');
            if (!bubbles.length) return;
            const last = bubbles[bubbles.length - 1];
            // Get text from the markdown content area
            const md = last.querySelector('.md, .message-content, .prose, .bot-message') || last;
            const text = md.innerText || md.textContent || '';
            if (!text.trim()) return;

            speak(text);
            // Trigger VRM expression if available
            if (window._aikoExprFromText) window._aikoExprFromText(text);
        });
        observer.observe(chatbot, { childList: true, subtree: true });
    }

    // ── UI buttons ────────────────────────────────────────────────────────────
    const btnBase = {
        position: 'fixed',
        bottom: '24px',
        zIndex: '99999',
        background: 'rgba(25, 15, 50, 0.9)',
        border: '1.5px solid rgba(155, 127, 212, 0.5)',
        borderRadius: '50%',
        width: '42px',
        height: '42px',
        fontSize: '20px',
        cursor: 'pointer',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        boxShadow: '0 4px 16px rgba(123, 79, 212, 0.35), inset 0 1px 0 rgba(255,255,255,0.1)',
        backdropFilter: 'blur(10px) saturate(1.2)',
        transition: 'all 0.25s ease',
        color: '#e8deff',
    };

    function buildMicButton() {
        const btn = document.createElement('button');
        btn.id = 'aiko-mic-btn';
        btn.innerHTML = '🎙️';
        btn.title = 'Click to speak (ASR)';
        Object.assign(btn.style, { ...btnBase, right: '68px' });
        document.body.appendChild(btn);

        const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRec) {
            btn.style.opacity = '0.3';
            btn.style.cursor = 'not-allowed';
            btn.title = 'Speech recognition not supported in this browser';
            return;
        }

        recognition = new SpeechRec();
        recognition.lang = ASR_LANG;
        recognition.interimResults = true;
        recognition.maxAlternatives = 1;
        recognition.continuous = false;

        recognition.onresult = (e) => {
            let transcript = '';
            for (let i = e.resultIndex; i < e.results.length; i++) {
                transcript += e.results[i][0].transcript;
            }
            if (!transcript.trim()) return;

            // Try multiple selectors for Gradio 4/5 textarea
            const inputEl =
                document.querySelector('#aiko-chatbot textarea') ||
                document.querySelector('.gradio-container textarea') ||
                document.querySelector('textarea[data-testid="textbox"]') ||
                document.querySelector('textarea[placeholder*="Say"]') ||
                document.querySelector('textarea');

            if (!inputEl) {
                console.warn('[aiko-asr] No input textarea found');
                return;
            }

            // Set value properly (Gradio uses reactive wrappers)
            const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
            nativeInputValueSetter.call(inputEl, transcript.trim());
            inputEl.dispatchEvent(new Event('input', { bubbles: true }));
            inputEl.dispatchEvent(new Event('change', { bubbles: true }));

            // Auto-submit after a short delay
            setTimeout(() => {
                const submitBtn =
                    document.querySelector('button[aria-label="Submit"]') ||
                    document.querySelector('button.submit') ||
                    document.querySelector('#component-submit-btn') ||
                    document.querySelector('[data-testid="chatbot-submit-button"]') ||
                    document.querySelector('button.primary') ||
                    [...document.querySelectorAll('button')].find(b =>
                        /submit|send|➤/i.test(b.getAttribute('aria-label') || b.textContent)
                    );
                if (submitBtn) {
                    submitBtn.click();
                    // Stop listening so we don't hear Aiko's reply
                    try { recognition.stop(); } catch (_) {}
                }
            }, 250);
        };

        recognition.onstart = () => {
            isListening = true;
            btn.innerHTML = '🔴';
            btn.style.background = 'rgba(180, 40, 80, 0.35)';
            btn.style.borderColor = 'rgba(255, 100, 120, 0.6)';
            btn.style.boxShadow = '0 0 20px rgba(220, 60, 100, 0.4)';
            window.speechSynthesis.cancel();
        };

        recognition.onend = () => {
            isListening = false;
            btn.innerHTML = '🎙️';
            btn.style.background = 'rgba(25, 15, 50, 0.9)';
            btn.style.borderColor = 'rgba(155, 127, 212, 0.5)';
            btn.style.boxShadow = '0 4px 16px rgba(123, 79, 212, 0.35)';
        };

        recognition.onerror = (e) => {
            console.warn('[aiko-asr]', e.error);
            isListening = false;
            btn.innerHTML = '⚠️';
            setTimeout(() => {
                btn.innerHTML = '🎙️';
                btn.style.background = 'rgba(25, 15, 50, 0.9)';
                btn.style.borderColor = 'rgba(155, 127, 212, 0.5)';
            }, 1500);
        };

        btn.addEventListener('click', () => {
            if (isListening) {
                recognition.stop();
            } else {
                try {
                    recognition.start();
                } catch (err) {
                    console.warn('[aiko-asr] start error:', err);
                }
            }
        });
    }

    function buildTTSToggle() {
        const btn = document.createElement('button');
        btn.id = 'aiko-tts-btn';
        btn.innerHTML = '🔊';
        btn.title = 'Toggle voice (TTS)';
        Object.assign(btn.style, { ...btnBase, right: '16px' });
        btn.addEventListener('click', () => {
            ttsEnabled = !ttsEnabled;
            btn.innerHTML = ttsEnabled ? '🔊' : '🔇';
            if (!ttsEnabled) window.speechSynthesis.cancel();
        });
        document.body.appendChild(btn);
    }

    // ── init ──────────────────────────────────────────────────────────────────
    function init() {
        // Load voices properly (Chrome needs this event)
        if (window.speechSynthesis.onvoiceschanged !== undefined) {
            window.speechSynthesis.onvoiceschanged = () => { voicesLoaded = true; };
        }
        // Force load once
        loadVoices();

        buildTTSToggle();
        buildMicButton();

        // Watch for chatbot container (Gradio renders it dynamically)
        waitFor('#aiko-chatbot', watchChatbot);
        waitFor('.chatbot', watchChatbot);
        waitFor('[data-testid="chatbot"]', watchChatbot);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
</script>
"""