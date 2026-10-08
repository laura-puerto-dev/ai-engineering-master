
# LangGraph — Stateful Workflows and Conversational Agents

Hands-on projects developed as part of my AI Engineering Master's program, exploring state management, conditional routing, error handling, and conversational agents with LangGraph.

## Projects

### 1. Customer Message Classifier

A stateful customer support workflow that classifies incoming messages as questions or complaints and routes them to specialized response nodes.

The example uses **NovaShop**, a fictional e-commerce company with predefined shipping and customer support policies.

**Key concepts:**
- State management with `TypedDict`
- Structured LLM output with Pydantic
- Conditional routing between graph nodes
- Retry loops with state updates
- Maximum retry limits and error handling
- Step-by-step execution using LangGraph streaming

**Tech stack:** Python, LangGraph, LangChain Ollama, Pydantic, Ollama (`llama3.1`).

#### Graph Architecture

![Message classifier graph](src/message_classifier/graph_classifier.png)

The workflow begins with a classification node. Depending on the classification result, the graph follows one of four possible paths:

| Route | Destination | Behavior |
|---|---|---|
| `question` | `answer_question` | Generates an answer using the fictional company context |
| `complaint` | `respond_to_complaint` | Generates an empathetic response to a customer complaint |
| `retry` | `prepare_retry` | Updates the state with retry instructions and returns to classification |
| `error` | `handle_error` | Returns a fallback response after exhausting the allowed attempts |

The graph uses explicit conditional edges to control transitions between nodes.

#### State Management

The workflow maintains a shared state containing:

| Field | Purpose |
|---|---|
| `message` | Original customer message |
| `category` | Classification result: question, complaint, or `None` |
| `answer` | Generated response |
| `classification_attempts` | Number of classification attempts |
| `classification_error` | Error recorded during classification |
| `retry_instructions` | Additional instructions for a subsequent attempt |

Each node returns updates to the shared state, which LangGraph propagates through the workflow.

#### Retry and Error Handling

The classifier supports a bounded retry mechanism to handle invalid classification results.

1. The `classify` node attempts to classify the customer message.
2. If classification succeeds, the graph routes to the appropriate response node.
3. If classification fails, the error and attempt count are recorded in the state.
4. The conditional routing function checks whether additional attempts are available.
5. If retries remain, `prepare_retry` adds instructions based on the previous error and returns control to `classify`.
6. If the maximum number of attempts is reached, the graph routes to `handle_error`.

The retry limit prevents an infinite loop.

The project also includes configurable **simulated classification failures** to demonstrate and test the retry and error-handling paths deterministically. These simulated failures are a testing mechanism, not actual LLM failures.

#### Execution Examples

**Question classification**

![Question execution](src/message_classifier/screenshots/question.png)

The message is classified as a question and routed to `answer_question`.

**Complaint classification**

![Complaint execution](src/message_classifier/screenshots/complaint.png)

The message is classified as a complaint and routed to `respond_to_complaint`.

Both examples show the executed nodes, classification result, number of attempts, and generated response.

#### Running the Project

**Prerequisites:**
- Python 3.12
- [uv](https://docs.astral.sh/uv/)
- [Ollama](https://ollama.com/)
- The `llama3.1` model available locally

Pull the model:

```bash
ollama pull llama3.1
```

From the `05-langgraph` directory, install the dependencies:

```bash
uv sync
```

Run the classifier:

```bash
uv run python src/message_classifier/classifier.py
```

The selected test message and retry settings can be changed in `src/message_classifier/config.py`.

**Test scenarios**

| `SIMULATED_FAILURES` | Expected behavior |
|---|---|
| `0` | Successful classification on the first attempt |
| `1` | One simulated failure; classification on the second attempt |
| `2` | Two simulated failures; classification on the third attempt |
| `3` | Three simulated failures; fallback through `handle_error` |

These scenarios assume the real classification succeeds when it is allowed to run. `MAX_ATTEMPTS` defaults to `3`.

To test both classification branches, set `TEST_MESSAGE` to either `QUESTION_MESSAGE` or `COMPLAINT_MESSAGE` in `config.py`.

#### Project Structure

```text
src/message_classifier/
├── classifier.py
├── config.py
├── prompts.py
├── graph_classifier.png
└── screenshots/
    ├── question.png
    └── complaint.png
```

- `classifier.py`: State definition, graph nodes, conditional routing, compilation, and execution.
- `config.py`: Test messages, fictional company context, and retry configuration.
- `prompts.py`: Prompt-building functions for classification, responses, and retries.
- `graph_classifier.png`: Generated graph visualization.
- `screenshots/`: Execution evidence for both classification branches.

#### Design Decisions

**Explicit graph control:** Conditional edges determine which node executes next, keeping routing behavior visible and predictable.

**Structured classification:** Pydantic constrains the classification result to the supported categories.

**Bounded retries:** Failed classification attempts are tracked in the shared state, with an explicit termination condition.

**Separation of concerns:** Graph orchestration, configuration, and prompt construction are kept in separate modules.

**Fictional business context:** NovaShop provides example policies for response generation without relying on real company systems or external integrations.

**Local execution:** Ollama enables the workflow to run with a locally hosted language model.

---

### 2. Conversational Agent with Memory and Tools

*Coming next.*
