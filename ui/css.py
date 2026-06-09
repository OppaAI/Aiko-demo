"""Shared CSS for the Gradio/Hugging Face Space interface."""

AIKO_CSS = r"""
:root {
  --aiko-bg: #080810;
  --aiko-panel: rgba(18, 14, 31, 0.78);
  --aiko-border: rgba(155, 127, 212, 0.28);
  --aiko-text: #dacdff;
  --aiko-muted: #8c7ab6;
  --aiko-accent: #b68cff;
}

body, .gradio-container {
  background: radial-gradient(circle at top, #1b1432 0, var(--aiko-bg) 44%, #050509 100%) !important;
  color: var(--aiko-text) !important;
}

#aiko-shell {
  max-width: 1180px;
  margin: 0 auto;
}

#aiko-avatar-card,
#aiko-chat-card {
  border: 1px solid var(--aiko-border) !important;
  border-radius: 22px !important;
  background: var(--aiko-panel) !important;
  box-shadow: 0 22px 80px rgba(0, 0, 0, 0.32) !important;
  overflow: hidden;
}

#aiko-vrm-frame {
  display: block;
  width: 100%;
  height: min(70vh, 720px);
  min-height: 460px;
  border: 0;
  background: #080810;
}

#aiko-audio {
  margin-top: 10px;
}

#aiko-audio audio {
  width: 100%;
  min-height: 34px;
  filter: hue-rotate(235deg) saturate(1.2);
}

#aiko-chatbot {
  min-height: 520px;
}

#aiko-chatbot .message,
#aiko-chatbot .bubble {
  border-radius: 18px !important;
}

textarea, input {
  background: rgba(10, 8, 18, 0.82) !important;
  color: var(--aiko-text) !important;
  border-color: var(--aiko-border) !important;
}

button.primary, button.variant-primary {
  background: linear-gradient(135deg, #7652d6, #bd7cff) !important;
  border: 0 !important;
}

#aiko-note {
  color: var(--aiko-muted);
  font-size: 0.9rem;
  text-align: center;
}
"""