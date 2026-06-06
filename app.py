import gradio as gr
import traceback
from core.wakeup import AikoWakeup

boot_error = None
result = None

try:
    result = AikoWakeup(text_mode=True).boot(
        on_loading=lambda k: print(f"[boot] loading: {k}"),
        on_done   =lambda k: print(f"[boot]    done: {k}"),
        on_skip   =lambda k: print(f"[boot]    skip: {k}"),
    )
    print(f"[boot] result={result}")
    print(f"[boot] think={result.think}")
    print(f"[boot] memorize={result.memorize}")
    think    = result.think
    memorize = result.memorize
except Exception as e:
    boot_error = traceback.format_exc()
    print(f"[boot] FAILED:\n{boot_error}")
    think    = None
    memorize = None

def chat(message, history):
    if think is None:
        return f"Boot failed:\n{boot_error}"
    tokens = []
    think.chat(message, token_callback=lambda t: tokens.append(t))
    return "".join(tokens)

demo = gr.ChatInterface(fn=chat, title="Aiko-chan ✨")
demo.launch(server_name="0.0.0.0")