# Model Selection

## Overview

This project focuses on selecting an appropriate LLM for a customer-facing
e-commerce assistant based on the requirements of the use case rather than
model size or benchmark scores alone.

The selection process considers:

- Input and output modality
- Reasoning complexity
- Context window requirements
- Latency and cost constraints
- Instruction following
- Hallucination control

## Approach

I first narrowed down the candidate models based on the technical and business
requirements of the assistant.

Three models were then evaluated against a set of representative test cases:

- Gemini 2.5 Flash Lite
- Qwen2.5 7B Instruct
- Mistral Small 3

The evaluation included calculations, hallucination traps, product
recommendations, formatting constraints, language adaptation and a more
complex conversational scenario.

## Outcome

Gemini 2.5 Flash Lite achieved the strongest overall result in the evaluation,
successfully handling all test cases while maintaining fast responses and a
low cost per interaction.

The main takeaway from this exercise was that model selection should be driven
by the actual requirements and evaluation cases of the application, rather
than assuming that a larger or more capable model is automatically the best
choice.

## Deliverable

The complete analysis, evaluation matrix and final recommendation are available
in [`model-selection.pdf`](./model-selection.pdf).
