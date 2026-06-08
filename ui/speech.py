SPEECH_JS = """
<script>
(function () {
    'use strict';

    // ── config ────────────────────────────────────────────────────────────────
    const TTS_RATE = 1.05, TTS_PITCH = 1.1, TTS_LANG = 'en-US', ASR_LANG = 'en-US';
    let ttsEnabled = true, lastSpoken = '', recognition = null, isListening = false;
    // Chrome blocks autoplay TTS unless a user gesture has occurred first.
    // We track this and defer the first speak() until after any click.
    let userHasInteracted = false;
    document.addEventListener('click', () => { userHasInteracted = true; }, { once: true });

    // ── utils ─────────────────────────────────────────────────────────────────
    function waitFor(getFn, cb, interval = 400, maxTries = 75) {
        let tries = 0;
        const id = setInterval(() => {
            const el = getFn();
            if (el) { clearInterval(id); cb(el); }
            if (++tries >= maxTries) clearInterval(id);
        }, interval);
    }

    function stripMarkdown(text) {
        return text
            .replace(/🔍\\s*Searching:.*/g, '')
            .replace(/\\*\\*(.*?)\\*\\*/g, '$1')
            .replace(/\\*(.*?)\\*/g, '$1')
            .replace(/`{1,3}[\\s\\S]*?`{1,3}/g, '')
            .replace(/#{1,6}\\s/g, '')
            .replace(/\\[([^\\]]+)\\]\\([^)]+\\)/g, '$1')
            .replace(/\\n+/g, ' ')
            .trim();
    }

    // ── TTS ───────────────────────────────────────────────────────────────────
    function getBestVoice() {
        const voices = window.speechSynthesis.getVoices();
        if (!voices.length) return null;
        const preferred = [
            v => v.lang === 'en-US' && /Google US English/i.test(v.name),
            v => v.lang === 'en-US' && /Samantha/i.test(v.name),
            v => v.lang === 'en-US' && /Zira/i.test(v.name),
            v => v.lang === 'en-US' && /female|woman/i.test(v.name),
            v => v.lang === 'en-US',
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
        const doSpeak = () => {
            const utt = new SpeechSynthesisUtterance(clean);
            utt.lang = TTS_LANG;
            utt.rate = TTS_RATE;
            utt.pitch = TTS_PITCH;
            const voice = getBestVoice();
            if (voice) utt.voice = voice;
            window.speechSynthesis.speak(utt);
        };
        // Defer until after user gesture if needed
        if (userHasInteracted) {
            setTimeout(doSpeak, 50);
        } else {
            document.addEventListener('click', () => setTimeout(doSpeak, 50), { once: true });
        }
    }

    // ── Gradio 6 bot bubble selector ──────────────────────────────────────────
    // Gradio 6 renders each message as a <div> with a data-role or wraps in
    // a container with class including "user"/"bot" or "assistant".
    // The most stable selectors across Gradio 4/5/6:
    //   - div[data-role="assistant"]          ← preferred, Gradio 4+ messages format
    //   - .message-wrap .bot                  ← Gradio 4 legacy
    //   - .bubble-wrap [class*="bot"]         ← Gradio 5
    // We query ALL and pick the last one by DOM order.
    function getLastBotText(chatbot) {
        const selectors = [
            '[data-role="assistant"] .prose',
            '[data-role="assistant"] .md',
            '[data-role="assistant"]',
            '.bot .prose',
            '.bot .md',
            '.bot',
        ];
        for (const sel of selectors) {
            const nodes = chatbot.querySelectorAll(sel);
            if (nodes.length) {
                const last = nodes[nodes.length - 1];
                const text = (last.innerText || last.textContent || '').trim();
                if (text) return text;
            }
        }
        return '';
    }

    // ── Chat observer ─────────────────────────────────────────────────────────
    function watchChatbot(chatbot) {
        let debounce = null;
        const observer = new MutationObserver(() => {
            clearTimeout(debounce);
            // Debounce: wait for streaming to settle (300ms of no DOM changes)
            debounce = setTimeout(() => {
                const text = getLastBotText(chatbot);
                if (text) speak(text);
                if (window._aikoExprFromText) window._aikoExprFromText(text);
            }, 300);
        });
        observer.observe(chatbot, { childList: true, subtree: true, characterData: true });
    }

    // ── Button styles ─────────────────────────────────────────────────────────
    // Gradio 6 renders inside a normal document (not iframe on HF Spaces local),
    // but the .gradio-container may scroll. Use fixed positioning but attach to
    // the shadow host or body carefully.
    const btnBase = {
        position: 'fixed',
        bottom: '24px',
        zIndex: '999999',
        background: 'rgba(25, 15, 50, 0.92)',
        border: '1.5px solid rgba(155, 127, 212, 0.55)',
        borderRadius: '50%',
        width: '44px',
        height: '44px',
        fontSize: '20px',
        cursor: 'pointer',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        boxShadow: '0 4px 16px rgba(123,79,212,0.35), inset 0 1px 0 rgba(255,255,255,0.1)',
        backdropFilter: 'blur(10px) saturate(1.2)',
        transition: 'all 0.25s ease',
        color: '#e8deff',
        fontFamily: 'sans-serif',
        lineHeight: '1',
    };

    function applyStyles(el, styles) {
        Object.assign(el.style, styles);
    }

    // ── Mic / ASR button ──────────────────────────────────────────────────────
    function buildMicButton() {
        const btn = document.createElement('button');
        btn.id = 'aiko-mic-btn';
        btn.innerHTML = '🎙️';
        btn.title = 'Click to speak';
        applyStyles(btn, { ...btnBase, right: '76px' });
        document.body.appendChild(btn);

        const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRec) {
            btn.style.opacity = '0.35';
            btn.style.cursor = 'not-allowed';
            btn.title = 'Speech recognition not supported';
            return;
        }

        recognition = new SpeechRec();
        recognition.lang = ASR_LANG;
        recognition.interimResults = false;   // final only — avoids partial-submit race
        recognition.maxAlternatives = 1;
        recognition.continuous = false;

        recognition.onresult = (e) => {
            const transcript = Array.from(e.results)
                .map(r => r[0].transcript).join('').trim();
            if (!transcript) return;

            // Gradio 6: textarea lives inside the form at the bottom
            const textarea =
                document.querySelector('#aiko-chatbot ~ * textarea') ||
                document.querySelector('.gradio-container textarea') ||
                document.querySelector('textarea[data-testid="textbox"]') ||
                document.querySelector('footer textarea') ||
                document.querySelector('textarea');

            if (!textarea) {
                console.warn('[aiko-asr] textarea not found');
                return;
            }

            const nativeSetter = Object.getOwnPropertyDescriptor(
                HTMLTextAreaElement.prototype, 'value'
            ).set;
            nativeSetter.call(textarea, transcript);
            textarea.dispatchEvent(new Event('input', { bubbles: true }));
            textarea.dispatchEvent(new Event('change', { bubbles: true }));

            setTimeout(() => {
                // Gradio 6 submit button — look for the Enter-submit button
                const submitBtn =
                    document.querySelector('button[aria-label="Submit"]') ||
                    document.querySelector('#aiko-chatbot ~ * button[type="submit"]') ||
                    document.querySelector('.gradio-container button.primary') ||
                    [...document.querySelectorAll('button')].find(b =>
                        /submit|send/i.test(b.getAttribute('aria-label') || '') ||
                        b.querySelector('svg[data-testid="send-icon"]')
                    );
                if (submitBtn && !submitBtn.disabled) {
                    submitBtn.click();
                }
                try { recognition.stop(); } catch (_) {}
            }, 200);
        };

        recognition.onstart = () => {
            isListening = true;
            userHasInteracted = true;
            btn.innerHTML = '🔴';
            applyStyles(btn, {
                background: 'rgba(180,40,80,0.35)',
                borderColor: 'rgba(255,100,120,0.6)',
                boxShadow: '0 0 20px rgba(220,60,100,0.4)',
            });
            window.speechSynthesis.cancel();
        };

        recognition.onend = () => {
            isListening = false;
            btn.innerHTML = '🎙️';
            applyStyles(btn, {
                background: 'rgba(25,15,50,0.92)',
                borderColor: 'rgba(155,127,212,0.55)',
                boxShadow: '0 4px 16px rgba(123,79,212,0.35)',
            });
        };

        recognition.onerror = (e) => {
            console.warn('[aiko-asr]', e.error);
            isListening = false;
            btn.innerHTML = '⚠️';
            setTimeout(() => {
                btn.innerHTML = '🎙️';
                applyStyles(btn, {
                    background: 'rgba(25,15,50,0.92)',
                    borderColor: 'rgba(155,127,212,0.55)',
                });
            }, 1800);
        };

        btn.addEventListener('click', () => {
            userHasInteracted = true;
            if (isListening) {
                recognition.stop();
            } else {
                try { recognition.start(); } catch (err) {
                    console.warn('[aiko-asr] start error:', err);
                }
            }
        });
    }

    // ── TTS toggle ────────────────────────────────────────────────────────────
    function buildTTSToggle() {
        const btn = document.createElement('button');
        btn.id = 'aiko-tts-btn';
        btn.innerHTML = '🔊';
        btn.title = 'Toggle voice output';
        applyStyles(btn, { ...btnBase, right: '24px' });
        btn.addEventListener('click', () => {
            userHasInteracted = true;
            ttsEnabled = !ttsEnabled;
            btn.innerHTML = ttsEnabled ? '🔊' : '🔇';
            if (!ttsEnabled) window.speechSynthesis.cancel();
        });
        document.body.appendChild(btn);
    }

    // ── init ──────────────────────────────────────────────────────────────────
    function init() {
        // Prime voice list (Chrome lazy-loads these)
        if (window.speechSynthesis.onvoiceschanged !== undefined) {
            window.speechSynthesis.onvoiceschanged = () => {};
        }
        window.speechSynthesis.getVoices();

        buildTTSToggle();
        buildMicButton();

        // Gradio 6: chatbot container — try elem_id first, then fallbacks
        const getChatbot = () =>
            document.querySelector('#aiko-chatbot .bubble-wrap') ||
            document.querySelector('#aiko-chatbot') ||
            document.querySelector('[id$="chatbot"]') ||
            document.querySelector('.chatbot') ||
            document.querySelector('[data-testid="chatbot"]');

        waitFor(getChatbot, watchChatbot);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
</script>
"""