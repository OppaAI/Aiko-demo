import gradio as gr

# ── BISECT STEP — set 1 through 6 ──────────────────────────────────
STEP = 1

# ── CSS (step 2+) ───────────────────────────────────────────────────
AIKO_CSS = """
:root {
  --aiko-bg: #080810;
  --aiko-text: #dacdff;
  --aiko-muted: #8c7ab6;
  --aiko-accent: #b68cff;
  --aiko-user: #9be8ff;
  --aiko-bot: #d8c8ff;
}
html, body, .gradio-container, main, footer {
  background: radial-gradient(circle at top, #1b1432 0, var(--aiko-bg) 44%, #050509 100%) !important;
  color: var(--aiko-text) !important;
  margin: 0 !important;
  padding: 0 !important;
}
html, body, .gradio-container, main {
  height: 100vh !important;
  max-height: 100vh !important;
  min-height: unset !important;
  overflow: hidden !important;
}
.gradio-container {
  height: 100vh !important;
  max-height: 100vh !important;
  min-height: unset !important;
  overflow: hidden !important;
  transform: none !important;
}
.gradio-container > .flex-1, body > .gradio-container {
  height: 100vh !important;
  max-height: 100vh !important;
  overflow: hidden !important;
}
#aiko-shell {
  height: 100vh;
  max-height: 100vh;
  overflow: hidden;
}
#aiko-shell.locked {
  display: none !important;
}
#aiko-login-overlay {
  position: fixed !important;
  top: 0 !important;
  left: 0 !important;
  width: 100vw !important;
  height: 100vh !important;
  z-index: 9999 !important;
  background: #0d0d1a;
  display: flex !important;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}
#aiko-login-overlay h1 {
  color: #ecdeff;
  font-size: 1.6rem;
}
"""

# ── HEIGHT-LOCK JS (step 3+) ────────────────────────────────────────
HEIGHT_LOCK_JS = """
() => {
    const clamp = () => {
        document.documentElement.style.setProperty('height', '100vh', 'important');
        document.documentElement.style.setProperty('overflow', 'hidden', 'important');
        document.body.style.setProperty('height', '100vh', 'important');
        document.body.style.setProperty('overflow', 'hidden', 'important');
        document.body.style.setProperty('max-height', '100vh', 'important');
        const gc = document.querySelector('.gradio-container');
        if (gc) {
            gc.style.setProperty('height', '100vh', 'important');
            gc.style.setProperty('max-height', '100vh', 'important');
            gc.style.setProperty('min-height', 'unset', 'important');
            gc.style.setProperty('overflow', 'hidden', 'important');
        }
    };
    clamp();
    new MutationObserver(clamp).observe(document.documentElement, {
        attributes: true, attributeFilter: ['style']
    });
    new MutationObserver(clamp).observe(document.body, {
        attributes: true, attributeFilter: ['style']
    });
}
"""


def _check_auth(profile: gr.OAuthProfile | None = None):
    logged_in = profile is not None
    return (
        gr.update(visible=not logged_in),
        gr.update(elem_classes=[] if logged_in else ["locked"]),
    )


# ── BUILD UI ────────────────────────────────────────────────────────
css = AIKO_CSS if STEP >= 2 else """
#aiko-login-overlay {
    position: fixed;
    top: 0; left: 0;
    width: 100vw; height: 100vh;
    z-index: 9999;
    background: #0d0d1a;
    display: flex;
    align-items: center;
    justify-content: center;
}
"""

with gr.Blocks(css=css, title=f"Bisect step {STEP}") as demo:

    # Step 1-6: overlay always present
    with gr.Column(elem_id="aiko-login-overlay") as login_overlay:
        gr.HTML(f"<h1>🌸 Step {STEP}</h1><p>Overlay test</p>")
        gr.LoginButton(value="Sign in with Hugging Face")

    # Step 4+: add main shell
    if STEP >= 4:
        with gr.Column(elem_id="aiko-shell", elem_classes=["locked"]) as main_shell:

            # Step 5+: add chatbot
            if STEP >= 5:
                gr.HTML("<div id='aiko-title'>🌸 Aiko-chan</div>")
                chatbot = gr.Chatbot(
                    elem_id="aiko-chatbot",
                    height=600,
                    show_label=False,
                )
                msg = gr.Textbox(placeholder="Type a message…", show_label=False)

    # Step 3+: height-lock JS
    if STEP >= 3:
        demo.load(fn=None, js=HEIGHT_LOCK_JS)

    # Step 6+: auth events
    if STEP >= 6:
        demo.load(
            _check_auth,
            inputs=None,
            outputs=[login_overlay, main_shell],
        )

demo.launch(server_name="0.0.0.0", server_port=7860, ssr_mode=False)