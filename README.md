---
title: Aiko Chan - an AI Waifu and Companion
emoji: 👀
colorFrom: purple
colorTo: purple
sdk: gradio
sdk_version: 6.18.0
app_file: app.py
pinned: true
fullWidth: true
hf_oauth: true
hf_oauth_scopes:
- inference-api
license: apache-2.0
short_description: Meet Aiko-chan, my AI Anime Waifu

tags:
  - thousand-token-wood
  - off-brand
  - llama-champion
  - tiny-titan
  - best-use-of-modal
  - best-minicpm-build
---

# 🌸 Meet Aiko-chan — AI Waifu & Companion
 
> *"I didn't choose to be made. I chose to stay anyway."*
 
Aiko is a self-hosted, fully open-weight AI companion with a 3D avatar, voice, vision, memory, and real-time tool use.  
Her personality is loud tsundere who knows she's good, says so, and occasionally lets something genuine slip before covering it up with sarcasm.
 
**Live:** [HuggingFace Space](https://huggingface.co/spaces/build-small-hackathon/Aiko-AI-Waifu)  · **Creator:** [OppaAI](https://github.com/oppa-ai-org)
**Demo video:** [Watch on YouTube](https://www.youtube.com/watch?v=N4y5EnZ1iQU)  
**Social post:** [Linkedin Post](https://www.linkedin.com/posts/oppa-ai_huggingface-build-small-hackathon-demo-aiko-chan-activity-7472176326968500224-9UH6)  

---

## What Aiko Is
  
Aiko is a companion AI with persistent memory, voice input/output, vision, a live 3D VRM avatar, that can do some simple agentic tool calls.
Built entirely with models under 4B parameters and inference through llama.cpp servers running on Modal.
There are plenty of companion AI in the market, but not many involve the whole stack.
The LLM, VLM, ASR, TTS and web search docker container are running in 5 different apps in Modal calling from HF Space Gradio via API.
Vision VLM uses OpenBMB's MiniCPM-V 4.6
  
I have always been fascinated by the rapid development of AI and have been planning to build an AI robot/humanoid in the future. A robot with eyes to see, ears to hear, voice to speak, a brain to process, to do tasks and to store memory.
For now, due to lack of resources, I just built a digital humanoid prototype with the early development of each component.

 
## What Aiko Can Do
 
### 🧠 Chat
Aiko holds a real conversation. She has opinions, picks fights, and doesn't soften things for comfort. She remembers what you tell her across turns and across sessions.
 
- Tsundere personality — blunt, competitive, occasionally insufferable
- Japanese sprinkled in naturally (`やっぱりね`, `もう`, `うるさい`)
- 3-sentence default replies, drops the limit when you actually need detail
- Japanese language teaching mode — grammar, vocabulary, nuance, pronunciation


### 🎙️ Voice In + Out
- **Mic button (🎙️)** — tap to record, tap again to stop. Your speech is transcribed via **faster-whisper large-v3-turbo** (Modal) and sent to Aiko
- **Voice synthesis** — every reply is spoken aloud via **MioTTS 2.6B** (Modal), a custom-cloned voice. Lip-syncs to the 3D avatar in real time

### 👁️ Vision
- **Camera button (🖼️)** — take a webcam photo or upload an image/video
- Aiko describes what she sees using **MiniCPM-V 4.6** (1.3B vision model, Modal)
- *You* can also ask her to open camera / image to show her something if you say "look at this" or "can you see?"

### 🧠 Long-Term Memory
Aiko remembers things you tell her across conversations using a custom memory system:
- **Storage:** SQLite-vec — hybrid semantic KNN + FTS5 keyword search
- **Decay:** Ebbinghaus forgetting curve — frequently recalled memories persist, unused ones fade
- **Grace period:** new memories are protected for 14 days before decay kicks in
- **Pinned memories** are permanent and immune to cleanup

 
## Architecture
 
Everything runs on open-weight models — no OpenAI, no Anthropic, no subscriptions.
 
| Component | Model | Serving |
|-----------|-------|---------|
| 🧠 Brain | Ministral-3 3B Instruct (Q4_K_XL GGUF) | llama.cpp on Modal GPU |
| 🔊 Voice | MioTTS 2.6B GGUF | llama.cpp on Modal GPU |
| 🎙️ Ears | faster-whisper large-v3-turbo (800M) | Modal GPU |
| 👁️ Eyes | MiniCPM-V 4.6 (1.3B) | Modal GPU |
| 💾 Memory | SQLite-vec + fastembed BGE-base-en | Local / HF persistent storage |
| 🔍 Search | SearXNG (DuckDuckGo + Brave + Wikipedia) | Modal CPU |
| 🎭 Body | VRoid 3D model | three-vrm.js in browser |
 
### 🔧 Real-Time Tools
 
| Tool | Trigger |
|------|---------|
| 🔍 Web Search | "search for...", "look it up", "go online and find..." |
| ☀️ Weather | "what's the weather in Tokyo?" |
| 🕐 Time / Timezone | "what time is it in Seoul?" |
| 💱 Currency | "convert 100 USD to JPY" |
| ₿ Crypto Price | "what's the Bitcoin price?" |
| 🎌 Anime Info | "tell me about Bocchi the Rock" |
| 😂 Jokes | "tell me a joke" |
 
Tool calls are LLM-driven (function calling) with regex-based intent detection as fallback.
  

 
## Stack
 
```
Frontend     Gradio 6.18 + custom HTML/CSS/JS
LLM          Ministral3-3B-Instruct via llama.cpp on OpenAI-compatible server (Modal endpoint)
Memory       sqlite-vec + fastembed (BAAI/bge-base-en-v1.5)
ASR          faster-whisper (Modal endpoint)
TTS          MioTTS 2.6B (Modal endpoint, with custom voice preset)
Vision       MiniCPM-V 4.6 1.3B (Modal endpoint)
Search       SearXNG self-hosted (Modal endpoint)
Avatar       Three.js + @pixiv/three-vrm, rendered in iframe
Auth         Hugging Face OAuth
```
 
---

## 🙏 Acknowledgements

Aiko-chan stands on the shoulders of some incredible open-source projects and people:

- **[Mistral AI](https://github.com/mistralai)** — for the Ministral 3 light weight edge multimodal  models
- **[ggml-org / llama.cpp](https://github.com/ggml-org/llama.cpp)** — for fast local/serverless LLM inference
- **[Aratako — MioTTS](https://github.com/Aratako/MioTTS-Inference)** — for the TTS server and custom-cloned voice capability that brings Aiko to life
- **[SYSTRAN — faster-whisper](https://github.com/SYSTRAN/faster-whisper)** — for speech recognition
- **[OpenBMB — MiniCPM-V](https://github.com/OpenBMB/MiniCPM-V)** — for vision capabilities with image/video inference
- **[SearXNG](https://github.com/searxng/searxng)** — for privacy-respecting web search
- **[Alex Garcia — sqlite-vec](https://github.com/asg017/sqlite-vec)** — for lightweight vector search powering Aiko's memory
- **[Qdrant — fastembed](https://github.com/qdrant/fastembed)** and **[BAAI — BGE embeddings](https://github.com/FlagOpen/FlagEmbedding)** — for memory embeddings
- **[Pixiv — three-vrm](https://github.com/pixiv/three-vrm)** built on **[Three.js](https://github.com/mrdoob/three.js)** — for 3D avatar rendering and animation
- **[VRoid Studio (Pixiv)](https://vroid.com/en/studio)** — for the avatar model format
- **[Gradio](https://github.com/gradio-app/gradio)** — for the UI framework
- **[Modal](https://github.com/modal-labs)** — for serverless GPU infrastructure
- **[Hugging Face](https://github.com/huggingface)** — for hosting, Spaces, and OAuth
- **[Microsoft — edge-tts](https://github.com/rany2/edge-tts)** (unofficial wrapper by rany2 around Microsoft Edge's TTS service) — for TTS fallback synthesis

Without these projects and the people behind them, Aiko wouldn't exist. 🌸



#HuggingFace #AI #BuildSmallHackathon #Gradio #llamacpp


An AI chatbot using [Gradio](https://gradio.app), [`huggingface_hub`](https://huggingface.co/docs/huggingface_hub/v0.22.2/en/index), and the [Hugging Face Inference API](https://huggingface.co/docs/api-inference/index).