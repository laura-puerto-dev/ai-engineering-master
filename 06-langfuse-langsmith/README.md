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


### 2. LangSmith and LLM Evaluation

This project extends the NovaShop LangGraph workflow with prompt versioning, classification evaluation, and LLM-as-Judge assessment.

**Key concepts:**
- Langfuse prompt management and production labels
- LangSmith execution tracing
- Reproducible evaluation datasets
- Classification accuracy and prompt version comparison
- LLM-as-Judge evaluation of generated responses
- Judge calibration and analysis of evaluation limitations

#### Prompt Management

Two versions of the `novashop-classification` prompt were published in Langfuse.

The second version addresses an ambiguous message about a previous return experience at another store, improving classification accuracy without introducing regressions in the evaluation dataset.

The workflow retrieves the prompt using the `production` label by default, allowing the active version to change without modifying application code. Evaluation scripts can also select a specific prompt version for reproducible experiments.

#### Classification Evaluation

A dataset of 20 labeled customer messages was used to compare the two prompt versions under the same model configuration.

| Metric | Prompt v1 | Prompt v2 |
|---|---:|---:|
| Correct classifications | 19/20 | 20/20 |
| Accuracy | 95% | 100% |

The evaluation records individual predictions, aggregate accuracy, model configuration, and a dataset SHA-256 hash to support reproducibility.

#### Response Evaluation with LLM-as-Judge

A separate dataset of 10 customer messages was used to evaluate the complete LangGraph workflow.

The assistant uses Llama 3.1 through Ollama to classify messages and generate responses. An independent LLM judge evaluates each response using three criteria, scored from 1 to 5:

- **Relevance:** How well the response addresses the customer's request.
- **Empathy and tone:** Whether the communication is appropriate and considerate.
- **Groundedness:** Whether factual claims about NovaShop are supported by the provided company context.

The evaluation also verifies classification accuracy and records the assistant model, judge model, prompt version, and dataset hash.

#### Judge Calibration and Findings

The initial judge used Llama 3.1. Its evaluation rubric was subsequently refined to distinguish factual grounding from relevance and tone.

Calibration tests revealed inconsistent judgments, particularly when responses combined valid company policies with unsupported claims.

GPT-4.1 mini was then evaluated using the refined rubric and demonstrated more consistent behavior across five controlled calibration cases.

The complete response evaluation was repeated with GPT-4.1 mini, preserving the earlier Llama 3.1 results for comparison.

All 10 messages were classified correctly. However, manual inspection showed that GPT-4.1 mini still assigned maximum groundedness scores to some responses containing unsupported claims, such as invented customer support contact channels or possible exceptions to the return policy.

**Key finding:** Successful judge calibration does not guarantee reliable evaluation of real application outputs. LLM-as-Judge scores should be interpreted alongside targeted test cases and manual review.

#### Running the Evaluations

Evaluate both classification prompt versions:

```bash
uv run python src/evaluation/evaluate_classification.py --prompt-version 1
uv run python src/evaluation/evaluate_classification.py --prompt-version 2
```

Compare classification results:

```bash
uv run python src/evaluation/compare_classification.py --baseline results/classification_v1.json --candidate results/classification_v2.json
```

Calibrate the LLM judge:

```bash
uv run python scripts/calibrate_judge.py
```

Evaluate the complete workflow:

```bash
uv run python scripts/run_response_evaluation.py --prompt-version 2
```

The response evaluation requires an OpenAI API key when using GPT-4.1 mini as the judge. Configure the required credentials in `.env` using `.env.example` as a reference.

#### Design Decisions

**Independent evaluation model:** Response generation and evaluation use different models to reduce reliance on self-evaluation.

**Version-controlled experiments:** Classification prompt versions can be selected explicitly, independently of the active production label.

**Reproducible datasets:** Evaluation results include dataset hashes and model configuration.

**Separate evaluation criteria:** Relevance, empathy, and groundedness are scored independently to avoid conflating factual correctness with communication quality.

**Transparent limitations:** Earlier judge results are preserved, and known evaluation failures are documented rather than hidden.
