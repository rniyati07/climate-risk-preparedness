<div align="center">
  <img src="https://via.placeholder.com/1200x300/0A0F1A/FFFFFF?text=ARIA+%E2%80%94+Climate+Risk+Preparedness+Advisor" alt="ARIA Banner">

  <h1>🌍 ARIA: Climate Risk Preparedness Advisor</h1>
  <p><em>Empowering communities with life-saving, AI-driven disaster intelligence before, during, and after a crisis strikes.</em></p>

  <!-- Badges -->
  <p>
    <img src="https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB" alt="React" />
    <img src="https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi" alt="FastAPI" />
    <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
    <img src="https://img.shields.io/badge/LangChain-1C3C3C?style=for-the-badge" alt="LangChain" />
    <img src="https://img.shields.io/badge/Groq-F55036?style=for-the-badge&logo=groq&logoColor=white" alt="Groq" />
  </p>
  <p>
    <a href="https://climate-risk-preparedness.vercel.app/"><strong>🔗 View Live Demo</strong></a>
  </p>
</div>

---

## 📖 About the Project

When a disaster strikes, critical seconds are lost parsing dense, 200-page government PDFs or endlessly scrolling through generic search results. **ARIA** solves this by translating complex National Disaster Management Authority (NDMA) protocols into instant, actionable, and personalized survival guidance. 

Built as a highly scalable **Agentic Multimodal RAG** (Retrieval-Augmented Generation) system, ARIA is designed for the general public facing imminent threats, local government agencies managing civic response, and relief organizations coordinating ground efforts. While its knowledge base currently focuses on the Indian subcontinent, its architecture is globally adaptable.

---

## ✨ Key Features

### 🧠 AI Intelligence
- **Real-Time Intent Classification:** The LLM actively distinguishes between general educational queries and urgent survival queries to adapt its response format.
- **Hybrid Retrieval Pipeline:** Always runs hyper-fast text retrieval (BGE embeddings), but dynamically lazy-loads a CLIP vision model if the query specifically requires image-based evacuation routes or maps.
- **Data Provenance:** Every response includes interactive citation badges showing exactly which government document and page number the information was sourced from.

### 🎨 UI/UX Engineering
- **Dynamic Hazard Theming:** The entire UI dynamically shifts color palettes based on the detected threat to visually anchor the user's psychological context:
  - 🌊 **Flood:** Cyan
  - 🌀 **Cyclone:** Amber
  - 🌡️ **Heatwave:** Crimson
  - 🌋 **Earthquake:** Brown
  - 🏜️ **Drought:** Gold
  - 🌐 **General:** Indigo
- **Cinematic Loading Experience:** A premium, pulsing radar-orb animation replaces standard loading spinners to convey systemic processing during emergency queries.
- **Session Persistence:** Full chat history is strictly saved to the user's local browser storage (`localStorage`), ensuring privacy and zero-cost scaling.

### 🛡️ Safety Design
- **Dual Response Modes:** 
  - *Preparedness Mode:* Renders highly structured, actionable "Before / During / After" phase cards for survival queries.
  - *Information Mode:* Renders clean, easily digestible markdown for general knowledge and contact numbers.
- **Factual Grounding:** Temperature is set strictly to `0.2` to prevent hallucination, forcing the LLM to rely exclusively on verified NDMA, IMD, and NDRF guidelines.

---

## 🏗️ System Architecture

ARIA uses a decoupled, serverless-ready architecture to ensure maximum uptime during crisis events.

```ascii
[User / Mobile Device] 
          │ 
     (HTTPS POST)
          ▼
  [React + Vite UI] ──(Dynamic Theme Engine & Safety Switch)
          │
      (REST API)
          ▼
  [FastAPI Backend] ──(Embed)──> [HF Inference API (BGE-Small)]
          │                                     │
      (Query)                                   ▼
          │                            [ChromaDB Vector Store]
          ▼                                     │
  [LLaMA 3.1 (Groq)] <──(Rerank)── [FlashRank Cross-Encoder]
          │
       (JSON)
          ▼
[Actionable UI Render]
```
**Architectural Rationale:** The heavy text-embedding workload is entirely offloaded to HuggingFace's Inference API. This keeps the core backend memory footprint drastically low (~200MB), allowing it to fit comfortably within free-tier PaaS limits and scale infinitely during demand spikes.

---

## 🛠️ Tech Stack

| Category | Technology | Purpose |
|----------|------------|---------|
| **Frontend** | React, Vite, Tailwind CSS, Framer Motion | Delivers a blazing fast, responsive, and cinematically animated user interface. |
| **Backend** | Python, FastAPI | Provides a highly concurrent, async REST API for processing RAG workflows. |
| **LLM Provider** | Groq (LLaMA 3.3 70B) | Ensures near-instantaneous token generation, crucial for time-sensitive emergencies. |
| **Embeddings** | HuggingFace API (BGE-Small) | Generates high-quality vector representations of text without consuming local server RAM. |
| **Vector DB** | ChromaDB (Local SQLite) | Stores and retrieves embedded document chunks instantly. Version-controlled via Git. |
| **Reranker** | FlashRank (TinyBERT) | Acts as a secondary cross-encoder to guarantee the most life-saving documents are prioritized. |

---

## 🚀 Getting Started

Follow these steps to run ARIA locally on your machine.

### Prerequisites
- Node.js (v18+)
- Python (3.10+)
- Git

### 1. Clone the Repository
```bash
git clone https://github.com/rniyati07/climate-risk-preparedness.git
cd climate-risk-preparedness
```

### 2. Backend Setup
```bash
# Create and activate a virtual environment
python -m venv venv
source venv/Scripts/activate  # (Windows)
# source venv/bin/activate    # (Mac/Linux)

# Install dependencies
pip install -r requirements.txt

# Start the FastAPI server
python server.py
```

### 3. Frontend Setup
```bash
# Open a new terminal and navigate to the frontend directory
cd frontend

# Install dependencies
npm install

# Start the Vite development server
npm run dev
```

---

## 🔐 Environment Variables

Create a `.env` file in the **root** of the project.

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | ✅ Yes | Free API key from Groq console to power the LLaMA model. |
| `HUGGINGFACE_TOKEN` | ✅ Yes | Free API token from HuggingFace to power the remote embedding API. |
| `ALLOWED_ORIGINS` | ❌ No | Commma separated list of allowed frontend URLs for CORS (Defaults to `*`). |
| `VITE_API_URL` | ❌ No | (Frontend `.env`) URL of the FastAPI backend. Defaults to `http://localhost:8000`. |

---

## 📁 Project Structure

```text
climate-risk-preparedness/
├── data/                  # Source PDFs and NDMA disaster guidelines
├── frontend/              # React/Vite web application
├── src/
│   ├── agents/            # LLM routing and real-time intent classification
│   ├── config/            # Centralized Pydantic environment settings
│   ├── ingestion/         # Document chunking, PDF parsing, and embedding logic
│   ├── rag/               # Core execution pipeline and prompt templates
│   └── retrieval/         # Vector DB querying and cross-encoder reranking
├── vectorstore/           # Pre-calculated ChromaDB SQLite database
├── server.py              # FastAPI server entry point
└── requirements.txt       # Python dependencies (CPU-optimized)
```

---

## ⚙️ How It Works

1. **The Query:** A user asks, *"How do I prepare my house for a cyclone?"*
2. **Classification:** The `risk_agent` instantly categorizes the hazard (`cyclone`) and the intent (`preparedness`).
3. **Retrieval:** The query is embedded via HuggingFace API and matched against the local ChromaDB vector store. 
4. **Reranking:** FlashRank evaluates the top 15 retrieved documents and strictly orders them by relevance to survival.
5. **Generation:** Groq's LLaMA model processes the top documents through a highly constrained system prompt, stripping out fluff and focusing purely on actionable steps.
6. **Rendering:** The React frontend detects the `preparedness` intent and the `cyclone` hazard, shifting the UI to an Amber theme and rendering the response in structured "Before, During, and After" phase cards.

---

## 📚 Disaster Coverage

ARIA is currently trained on the following localized hazard profiles:

| Hazard | Theme Color | Primary Sources |
|--------|-------------|-----------------|
| **Flood** | 🌊 Cyan | NDMA Flood Guidelines, State Evacuation Protocols |
| **Cyclone** | 🌀 Amber | IMD Cyclone Warnings, NDRF Checklists |
| **Heatwave** | 🌡️ Crimson | NDMA Heat Action Plans, Local Health Advisories |
| **Earthquake** | 🌋 Brown | NDMA Seismic Safety Guides, Structural Checklists |
| **Drought** | 🏜️ Gold | Agricultural Advisories, Water Conservation Protocols |

---

## 🌐 Deployment

ARIA is fully optimized for free-tier cloud deployment.

1. **Database:** Because the vector dataset is highly curated and <100MB, the `chroma_db` is committed directly to GitHub. This eliminates the need for expensive cloud vector databases.
2. **Backend (Render):** Deploy the root repository to Render as a Web Service. The `requirements.txt` is strictly CPU-optimized to ensure lightning-fast builds (<2 mins) and prevent memory crashes.
3. **Frontend (Vercel):** Deploy the `frontend/` directory to Vercel. Add your Render backend URL to Vercel's `VITE_API_URL` environment variable.

---

## 🛣️ Roadmap

- [ ] **Multilingual Support:** Integrate seamless translation to support Tamil, Hindi, and regional dialects.
- [ ] **Real-Time Weather API:** Connect to IMD APIs to provide live alert banners for the user's geolocation.
- [ ] **SMS Gateway:** Allow users to text queries to ARIA when internet access is down during a crisis.
- [ ] **Mobile App:** Package the web experience into an offline-capable PWA.

---

## 🤝 Contributing

Contributions are what make the open-source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

---

## 🙏 Acknowledgements

- **[National Disaster Management Authority (NDMA)](https://ndma.gov.in/)** for their comprehensive, life-saving guidelines.
- **[India Meteorological Department (IMD)](https://mausam.imd.gov.in/)** for extreme weather operational protocols.
- **[Groq](https://groq.com/)** for providing LPU inference speeds that make real-time emergency chatbots possible.
- **[HuggingFace](https://huggingface.co/)** for open-source embedding models.
- **[Chroma](https://www.trychroma.com/)** for lightweight, edge-ready vector search.
