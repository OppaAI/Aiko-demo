SPEECH_JS = """
<script>
(function () {
    const TTS_RATE = 1.05, TTS_PITCH = 1.1, TTS_LANG = 'en-US', ASR_LANG = 'en-US';
    let ttsEnabled = true, lastSpoken = '', recognition = null, isListening = false;

    function waitFor(selector, cb, interval=200, maxTries=50) {
        let tries = 0;
        const id = setInterval(() => {
            const el = document.querySelector(selector);
            if (el) { clearInterval(id); cb(el); }
            if (++tries >= maxTries) clearInterval(id);
        }, interval);
    }

    function stripMarkdown(text) {
        return text
            .replace(/\U0001f50d Searching:.*/g, '')
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
        utt.lang = TTS_LANG; utt.rate = TTS_RATE; utt.pitch = TTS_PITCH;
        const voices = window.speechSynthesis.getVoices();
        const female = voices.find(v => v.lang.startsWith('en') && /female|woman|girl/i.test(v.name))
                    || voices.find(v => v.lang.startsWith('en'));
        if (female) utt.voice = female;
        window.speechSynthesis.speak(utt);
    }

    function watchChatbot(chatbot) {
        const observer = new MutationObserver(() => {
            const bubbles = chatbot.querySelectorAll('.message.bot,[data-testid="bot"] .md');
            if (!bubbles.length) return;
            const last = bubbles[bubbles.length - 1];
            const text = last.innerText || last.textContent || '';
            speak(text);
            if (window._aikoExprFromText) window._aikoExprFromText(text);
        });
        observer.observe(chatbot, { childList: true, subtree: true });
    }

    const btnBase = {
        position: 'fixed', bottom: '22px', zIndex: '9999',
        background: 'rgba(30,15,55,0.85)',
        border: '1.5px solid rgba(155,127,212,0.5)',
        borderRadius: '50%', width: '38px', height: '38px',
        fontSize: '18px', cursor: 'pointer',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        boxShadow: '0 2px 12px rgba(123,79,212,0.3)',
        backdropFilter: 'blur(8px)',
    };

    function buildMicButton() {
        const btn = document.createElement('button');
        btn.id = 'aiko-mic-btn';
        btn.innerHTML = '\U0001f3a4';
        btn.title = 'Click to speak';
        Object.assign(btn.style, { ...btnBase, right: '60px' });
        document.body.appendChild(btn);

        const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRec) { btn.style.opacity = '0.4'; btn.style.cursor = 'not-allowed'; return; }

        recognition = new SpeechRec();
        recognition.lang = ASR_LANG;
        recognition.interimResults = false;
        recognition.maxAlternatives = 1;

        recognition.onresult = e => {
            const transcript = e.results[0][0].transcript.trim();
            if (!transcript) return;
            const inputEl = document.querySelector('.gradio-container textarea')
                         || document.querySelector('textarea');
            if (!inputEl) return;
            const proto = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value');
            proto.set.call(inputEl, transcript);
            inputEl.dispatchEvent(new Event('input', { bubbles: true }));
            setTimeout(() => {
                const submitBtn =
                    document.querySelector('button.submit') ||
                    document.querySelector('#component-submit-btn') ||
                    document.querySelector('[data-testid="submit-btn"]') ||
                    [...document.querySelectorAll('button')]
                        .find(b => b.getAttribute('aria-label') === 'Submit'
                               || b.textContent.trim() === 'Submit');
                if (submitBtn) submitBtn.click();
            }, 200);
        };

        recognition.onstart = () => {
            isListening = true;
            btn.innerHTML = '\U0001f534';
            btn.style.background = 'rgba(180,30,80,0.25)';
            window.speechSynthesis.cancel();
        };
        recognition.onend = () => {
            isListening = false;
            btn.innerHTML = '\U0001f3a4';
            btn.style.background = 'rgba(30,15,55,0.85)';
        };
        recognition.onerror = e => {
            console.warn('[aiko-asr]', e.error);
            isListening = false;
            btn.innerHTML = '\U0001f3a4';
            btn.style.background = 'rgba(30,15,55,0.85)';
        };

        btn.addEventListener('click', () => {
            if (isListening) recognition.stop();
            else try { recognition.start(); } catch(e) { console.warn(e); }
        });
    }

    function buildTTSToggle() {
        const btn = document.createElement('button');
        btn.innerHTML = '\U0001f50a';
        btn.title = 'Toggle voice';
        Object.assign(btn.style, { ...btnBase, right: '12px' });
        btn.addEventListener('click', () => {
            ttsEnabled = !ttsEnabled;
            btn.innerHTML = ttsEnabled ? '\U0001f50a' : '\U0001f507';
            if (!ttsEnabled) window.speechSynthesis.cancel();
        });
        document.body.appendChild(btn);
    }

    window.addEventListener('load', () => {
        if (window.speechSynthesis.onvoiceschanged !== undefined)
            window.speechSynthesis.onvoiceschanged = () => {};
        buildTTSToggle();
        buildMicButton();
        waitFor('.chatbot,[data-testid="chatbot"]', watchChatbot);
    });
})();
</script>
"""