"""Shared CSS for the Gradio/Hugging Face Space interface."""

AIKO_CSS = r"""
:root {
  --aiko-bg: #080810;
  --aiko-panel: rgba(18, 14, 31, 0.86);
  --aiko-panel-solid: #100d1d;
  --aiko-border: rgba(155, 127, 212, 0.34);
  --aiko-text: #dacdff;
  --aiko-muted: #8c7ab6;
  --aiko-accent: #b68cff;
  --aiko-user: #322255;
  --aiko-bot: #191329;
}

html,
body,
.gradio-container,
main,
footer {
  background: radial-gradient(circle at top, #1b1432 0, var(--aiko-bg) 44%, #050509 100%) !important;
  color: var(--aiko-text) !important;
}

.gradio-container *,
.gradio-container .prose,
.gradio-container label {
  color: var(--aiko-text);
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

#aiko-title h1,
#aiko-title {
  text-align: center;
  color: var(--aiko-accent) !important;
}

#aiko-chat-card,
#aiko-chat-card > div,
#aiko-chat-card .block,
#aiko-chat-card .wrap,
#aiko-chat-card .form,
#aiko-chat-card .contain,
#aiko-chat-card .chatbot,
#aiko-chatbot,
#aiko-chatbot > div,
#aiko-chatbot div {
  background: var(--aiko-panel-solid) !important;
  border-color: var(--aiko-border) !important;
}

#aiko-chatbot {
  min-height: 520px;
  border-radius: 16px !important;
}

#aiko-chatbot .message,
#aiko-chatbot .bubble,
#aiko-chatbot [data-testid="bot"],
#aiko-chatbot [data-testid="user"] {
  border-radius: 18px !important;
  color: var(--aiko-text) !important;
}

#aiko-chatbot .message.user,
#aiko-chatbot .bubble.user,
#aiko-chatbot [data-testid="user"] {
  background: var(--aiko-user) !important;
}

#aiko-chatbot .message.bot,
#aiko-chatbot .bubble.bot,
#aiko-chatbot [data-testid="bot"] {
  background: var(--aiko-bot) !important;
}

#aiko-input-row,
#aiko-input-row > div,
#aiko-mic,
#aiko-mic > div,
#aiko-audio,
#aiko-audio > div,
#aiko-audio .wrap,
#aiko-audio .container,
#aiko-audio div,
#aiko-mic div {
  background: var(--aiko-panel-solid) !important;
  border-color: var(--aiko-border) !important;
}

#aiko-audio audio {
  width: 100%;
  min-height: 34px;
  filter: hue-rotate(235deg) saturate(1.2);
}

textarea,
input,
#aiko-input-row textarea,
#aiko-input-row input {
  background: rgba(10, 8, 18, 0.92) !important;
  color: var(--aiko-text) !important;
  border-color: var(--aiko-border) !important;
}

textarea::placeholder,
input::placeholder {
  color: var(--aiko-muted) !important;
}

button.primary,
button.variant-primary,
#aiko-send {
  background: linear-gradient(135deg, #7652d6, #bd7cff) !important;
  border: 0 !important;
  color: #fff !important;
}

#aiko-note {
  color: var(--aiko-muted) !important;
  font-size: 0.9rem;
  text-align: center;
}
"""