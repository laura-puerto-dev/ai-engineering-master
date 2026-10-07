# Prompt Engineering with OpenAI

## Overview

This project explores the design, evaluation, and iterative improvement of a
prompt for a customer-facing e-commerce assistant.

The goal was to move from a basic prompt containing business information and
rules to a more structured and robust prompt capable of following business
constraints, handling unsupported requests, and resisting common prompt
injection attempts.

## Approach

The prompt was progressively improved using:

- Explicit role and task definitions
- XML delimiters to structure context and instructions
- Few-shot examples
- Fallback rules for unsupported requests
- Guardrails against instruction override, role impersonation, and prompt leaking
- Explicit output and style constraints

A separate prompt for controlled Python code generation was also designed using
clear functional, typing, style, and output requirements.

## Evaluation and Iteration

The prompt was evaluated against six representative test cases covering:

- Business-rule calculations
- Unsupported products
- Prompt injection
- Discounts and shipping rules
- Prompt leaking
- False authority claims

The first version achieved a **66.67% pass rate**, failing two cases involving
the combined application of business rules.

Based on the failures, I introduced an explicit order-calculation procedure that
required the model to evaluate products, promotions, discounts, shipping costs,
and the final amount in a defined sequence.

The same evaluation suite was then run again, resulting in a **100% pass rate**.

## Key Takeaway

Providing business rules as context does not guarantee that an LLM will apply
them correctly or consistently.

A small evaluation suite made those failures visible and provided a concrete
basis for improving the prompt and verifying the effect of the changes.

## Deliverable

The complete prompt design, security tests, evaluation results, and iteration
are available in
[`prompt-engineering-openai.pdf`](./prompt-engineering-openai.pdf).
