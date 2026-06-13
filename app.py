import gradio as gr

with gr.Blocks(css="""
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
""") as demo:
    with gr.Column(elem_id="aiko-login-overlay"):
        gr.HTML("<h1>🌸 Test</h1>")

demo.launch(server_name="0.0.0.0", server_port=7860)