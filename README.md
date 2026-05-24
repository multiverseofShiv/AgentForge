AgentForge

> A production-grade multi-agent AI platform where specialized LLM agents collaborate to research, write, review, and query data autonomously.



   


---

What is AgentForge?

AgentForge is an open-source agentic AI system.

Instead of asking one LLM to do everything, AgentForge spins up a team of specialized agents — a Researcher, Writer, Reviewer, and SQL Agent — coordinated by a Supervisor that decides who does what next.

Think of it like a small newsroom inside your API.

🔍 Researcher searches the web, Wikipedia, and arXiv

✍️ Writer drafts content from the research

🧠 Reviewer scores the draft and sends it back for revision if it isn't good enough

🗄️ SQL Agent answers database questions (with human approval before execution)

🧭 Supervisor routes work between agents using a fine-tuned lightweight model


You send one request.
You watch the agents work live over WebSocket.
You get a polished final answer back.


---

Why does this exist?

Most "agent" demos are toy scripts that break in production.

AgentForge is designed to demonstrate real-world agentic patterns:

Problem How AgentForge Solves It

Agents loop forever and burn tokens Bounded Reflexion critic loop (max 3 iterations)
Agents execute dangerous actions autonomously Human-in-the-loop approval before SQL execution
Large router LLMs are expensive and slow QLoRA fine-tuned Phi-3-mini router (~12x cheaper, ~6x faster)
Hard to debug agent decisions Live WebSocket trajectories + Langfuse traces
Framework lock-in Same workflow implemented in LangGraph and CrewAI


It is also the agentic half of a two-project GenAI portfolio
(companion project: DocMind for production RAG systems).


---

Architecture

Component Diagram (UML)

classDiagram
direction TB

class FastAPI_App {
  +POST /api/v1/tasks
  +POST /api/v1/tasks/{id}/approve
  +WS /api/v1/ws/tasks/{id}
}

class StateGraph {
  <<LangGraph>>
  +checkpointer: MemorySaver
  +interrupt_before: [sql_agent]
  +compile()
  +astream_events()
}

class AgentState {
  <<TypedDict>>
  +task: str
  +research_notes: str
  +draft: str
  +review_feedback: str
  +next_agent: str
  +iteration_count: int
  +status: str
  +human_approval_needed: bool
}

class Supervisor {
  <<router>>
  -llm: PhiThreeMini_QLORA
  +route(state): SupervisorDecision
}

class Researcher {
  <<worker>>
  -tools: [web_search, wiki, arxiv]
}

class Writer {
  <<worker>>
  -temperature: 0.7
}

class Reviewer {
  <<critic>>
  +returns: ReviewDecision
}

class SQLAgent {
  <<worker>>
  -guard: ReadOnlyRegex
}

class ToolLayer {
  <<@tool>>
  +web_search()
  +search_wikipedia()
  +search_arxiv()
  +execute_sql()
  +generate_chart()
}

class Langfuse {
  <<observability>>
}

FastAPI_App --> StateGraph : invokes
StateGraph o-- AgentState : owns
StateGraph --> Supervisor : entry

Supervisor --> Researcher
Supervisor --> Writer
Supervisor --> Reviewer
Supervisor --> SQLAgent

Researcher --> Supervisor : returns
Writer --> Supervisor : returns
Reviewer --> Supervisor : returns
SQLAgent --> Supervisor : returns

Researcher ..> ToolLayer : uses
SQLAgent ..> ToolLayer : uses

StateGraph ..> Langfuse : traces


---

Sequence Diagram — Request Lifecycle

sequenceDiagram
autonumber

actor User

participant API as FastAPI
participant G as StateGraph
participant S as Supervisor
participant R as Researcher
participant W as Writer
participant V as Reviewer
participant Q as SQL Agent
participant H as Human Approver

User->>API: POST /tasks {task}

API->>G: invoke(AgentState)

G->>S: route(state)
S-->>G: researcher

G->>R: run
R-->>G: research_notes

loop critic loop (max 3)
    G->>W: run
    W-->>G: draft

    G->>V: run
    V-->>G: ReviewDecision

    alt revise && iter < 3
        Note right of V: Send feedback back to Writer
    else accept or cap hit
        Note right of V: Exit loop
    end
end

Note over G,Q: interrupt_before=[sql_agent]

G-->>API: paused (approval_required)
API-->>User: 200 (approval_required=true)

User->>H: Review proposed SQL
H->>API: POST /tasks/{id}/approve

API->>G: resume(thread_id)

G->>Q: run
Q-->>G: result
G-->>API: final_output
API-->>User: stream via WebSocket


---

Features

🧠 Multi-agent graph — LangGraph StateGraph with cycles and conditional routing

🔍 Specialized agents — Researcher, Writer, Reviewer, and SQL Agent

🔁 Self-correction loop — Writer ↔ Reviewer Reflexion cycle

👤 Human-in-the-loop — Approval required before dangerous SQL execution

⚡ Live progress streaming — Real-time WebSocket agent events

🛡️ Safe tools — Typed @tool functions with Pydantic validation

💸 Fine-tuned lightweight router — QLoRA Phi-3-mini replacing heavyweight routing LLMs

📊 Observability — Langfuse traces for every node, tool call, and LLM invocation

🔄 Framework comparison — Same workflow implemented in CrewAI

✅ Tested + evaluated — Pytest suite + trajectory/outcome golden sets



---

Quick Start

Prerequisites

Python 3.11

Docker (optional, for Langfuse)

A free Groq API Key

A free Tavily API Key



---

Setup

# Clone repository
git clone https://github.com/<your-user>/AgentForge.git

cd AgentForge

# Create virtual environment
python -m venv .venv

# Activate environment

# Windows PowerShell
.\.venv\Scripts\Activate.ps1

# macOS / Linux
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure secrets
cp .env.example .env

# Add:
# GROQ_API_KEY=
# TAVILY_API_KEY=
# LANGFUSE_PUBLIC_KEY=
# LANGFUSE_SECRET_KEY=

# Run server
uvicorn app.main:app --reload

API docs:

http://localhost:8000/docs


---

Try It

curl -X POST http://localhost:8000/api/v1/tasks \
-H "Content-Type: application/json" \
-d '{
  "task": "Research recent advances in RAG and write a 200-word summary."
}'


---

Watch Agents Work Live

Open:

demo/ws_demo.html

Example trajectory:

[Supervisor] -> researcher
[Researcher] tool: web_search
[Researcher] tool: search_arxiv

[Supervisor] -> writer
[Writer] draft ready

[Supervisor] -> reviewer
[Reviewer] decision=revise score=6

[Supervisor] -> writer
[Reviewer] decision=accept score=9

[Supervisor] -> done


---

Project Structure

AgentForge/
│
├── app/
│   ├── main.py
│   ├── api/routes/
│   ├── agents/
│   ├── tools/
│   ├── prompts/
│   ├── services/llm.py
│   ├── guardrails/
│   ├── core/config.py
│   └── models/schemas.py
│
├── crewai_alternative/
│   └── crew.py
│
├── finetune/
│
├── evals/
│
├── demo/
│   └── ws_demo.html
│
├── tests/
│
├── requirements.txt
└── README.md

Highlights

Path Purpose

main.py FastAPI entry point
api/routes/ REST + WebSocket routes
agents/ LangGraph nodes and workflows
tools/ Typed @tool functions
prompts/ System prompts per agent
services/llm.py LLM provider factory
guardrails/ Input/output safety
finetune/ QLoRA training notebooks/scripts
evals/ Agent evaluation scripts
tests/ Pytest suite



---

Tech Stack

Layer Tool

Orchestration LangGraph 1.1
Chains / Tools LangChain 1.2
API FastAPI + Uvicorn
LLM (Prod) Groq (Llama 3.1 70B)
LLM (Fallback) Ollama (Llama 3.1 8B, Phi-3-mini)
Validation Pydantic 2.9
Search Tavily, DuckDuckGo, Wikipedia, arXiv
Database SQLAlchemy + SQLite
Fine-tuning Unsloth + PEFT + TRL (QLoRA, 4-bit)
Observability Langfuse
Alternative Framework CrewAI
Testing pytest + pytest-asyncio



---

Results

Metric Value

Router accuracy (Phi-3 zero-shot baseline) ~78%
Router accuracy (QLoRA fine-tuned) 94%
Router latency (Phi-3 local) ~80 ms
Router latency (GPT-4o-mini) ~500 ms
Cost per 1K routing decisions ~$0 vs ~$0.05
Quality lift from critic loop +18%


Reproduce:

python finetune/eval_router.py

python evals/agent_eval.py


---

Roadmap

[x] Scaffold, state, schemas, LLM factory

[x] Tools (web, wiki, arXiv, SQL, chart)

[x] Agents (researcher, writer, reviewer, SQL)

[x] Supervisor + StateGraph + conditional edges

[ ] Writer ↔ Reviewer critic loop

[ ] Human-in-the-loop checkpointing

[ ] WebSocket live progress UI

[ ] CrewAI alternative implementation

[ ] Langfuse tracing

[ ] QLoRA router fine-tuning integration

[ ] Agent evaluation pipeline

[ ] Docker + Render deployment

[ ] Demo GIF + Loom walkthrough



---

Contributing
This is primarily a learning + portfolio project, but contributions are welcome.

If you:

find a bug,

want a new agent,

improve routing logic,

add better guardrails,

improve observability,


feel free to open an issue or submit a PR.


---

License

This project is licensed under the MIT License.

See the LICENSE file for details.


---

Acknowledgements

Built on top of the excellent work from:

LangChain

LangGraph

CrewAI

Unsloth


Huge thanks to the open-source AI ecosystem.
