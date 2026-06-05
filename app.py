import gradio as gr

def chat(message, history):
    return f"Aiko-chan says: {message}"

demo = gr.ChatInterface(fn=chat, title="Aiko-chan ✨")
demo.launch(server_name="0.0.0.0")