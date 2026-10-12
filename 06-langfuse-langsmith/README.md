# Langfuse & LangSmith — LLM Observability and Evaluation

Observability, prompt management, and evaluation of LLM-powered applications using Langfuse and LangSmith.

The projects build on the NovaShop customer message classifier developed in Module 05, extending its LangGraph workflow with execution tracing, performance analysis, and evaluation capabilities.

## Projects

### 1. Langfuse Observability

A LangGraph-based customer support workflow instrumented with Langfuse to capture end-to-end execution traces and analyze model behavior, token usage, latency, and retry handling.

The implementation reuses **NovaShop**, a fictional e-commerce company whose workflow classifies customer messages as questions or complaints and routes them to specialized response nodes.

**Key concepts:**
- End-to-end tracing of LangGraph executions
- Node-level visibility into classification and response generation
- Token usage and execution latency analysis
- Conditional routing and retry inspection
- Configurable trace names for identifying execution scenarios

**Tech stack:** Python, LangGraph, LangChain, Langfuse, Ollama (`llama3.1`), Pydantic.

#### Observability Architecture

The workflow is instrumented using Langfuse's `CallbackHandler`, attached to the LangGraph execution.

This captures the complete execution hierarchy, including classification, conditional routing, response generation, and retry handling, without modifying the graph's business logic.

Each execution is assigned a configurable trace name to distinguish scenarios in the Langfuse dashboard.

#### Trace Analysis

Three execution scenarios were analyzed:

| Scenario | Latency | Tokens |
|---|---:|---:|
| Complaint classification and response | 7.17 s | 564 |
| Question classification and response | 3.35 s | 448 |
| Complaint with two simulated classification failures | 4.86 s | 623 |

The retry scenario recorded the highest token usage, while the standard complaint scenario had the highest latency. This illustrates that token consumption and execution time do not necessarily increase together.

In the retry scenario, the first two classification attempts fail deterministically before the LLM is invoked. The third attempt performs the actual classification with additional retry instructions, followed by response generation.

The additional instructions increase the classification prompt size, while the generated response length also affects total token consumption.

Since the model runs locally through Ollama, token usage does not represent billed API costs.

#### Running the Project

**Prerequisites:**
- Python 3.12
- [uv](https://docs.astral.sh/uv/)
- [Ollama](https://ollama.com/) running locally
- The `llama3.1` model available locally
- Langfuse credentials

Pull the model if needed:

```bash
ollama pull llama3.1
```

From the `06-langfuse-langsmith` directory, install dependencies:

```bash
uv sync
```

Configure the environment variables using `.env.example` as a reference.

Run the workflow:

```bash
uv run python src/message_classifier/classifier.py
```

Execution scenarios can be configured in `src/message_classifier/config.py`:

| Setting | Purpose |
|---|---|
| `TEST_MESSAGE` | Selects the customer message to process |
| `TRACE_NAME` | Identifies the execution in Langfuse |
| `SIMULATED_FAILURES` | Controls the number of simulated classification failures |
| `MAX_ATTEMPTS` | Limits classification retries |

#### Project Structure

```text
src/message_classifier/
├── __init__.py
├── classifier.py
├── config.py
└── prompts.py
```

- `classifier.py`: LangGraph workflow, classification and response nodes, conditional routing, tracing, and execution.
- `config.py`: Test messages, trace names, retry configuration, and fictional company context.
- `prompts.py`: Prompt construction for classification, customer responses, and retry instructions.

#### Design Decisions

**Workflow-level instrumentation:** The Langfuse callback handler is attached to the graph execution rather than individual nodes, preserving the full execution hierarchy.

**Separation of concerns:** Observability is integrated through execution callbacks without modifying the graph's classification, routing, or response-generation logic.

**Configurable trace identification:** Execution names are defined in configuration to distinguish scenarios without changing the graph implementation.

**Deterministic failure simulation:** Simulated failures allow retry paths to be inspected without depending on unpredictable LLM errors.

**Local inference:** Ollama provides local model execution without per-request API charges.
