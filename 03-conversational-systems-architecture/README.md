# Conversational Systems Architecture

## Overview

This project focuses on designing the architecture of an AI-powered product
recommendation assistant before moving into implementation.

The goal was to translate product requirements into clear software
responsibilities and organize them into architectural layers with well-defined
boundaries.

## Requirements

The system requirements include both functional and non-functional concerns,
such as:

- Recommending a product based on customer preferences
- Checking real-time stock before making a recommendation
- Handling cases where no suitable product is available
- Persisting the final recommendation
- Meeting response-time requirements
- Protecting stored customer data

## Architecture

The system responsibilities were separated into four layers:

- **Presentation** — receives chat requests and returns responses
- **Application** — coordinates the conversation and decides the next action
- **Domain** — contains the business rules used to determine suitable products
- **Infrastructure** — integrates with external systems such as stock services
  and LLM providers

The proposed structure also isolates LLM integrations behind dedicated
infrastructure components, keeping provider-specific concerns separate from
business logic.

## Agent Reasoning

A ReAct-style agent was considered appropriate because the interaction does not
necessarily follow a predefined sequence.

The agent may need to decide dynamically which action to take next based on the
information collected during previous steps of the conversation.

## Key Takeaway

Designing an AI application is not only about connecting an LLM to an interface.

Separating orchestration, business rules, external integrations, and
presentation concerns makes the system easier to reason about and provides a
cleaner foundation for evolving or replacing individual components.

## Deliverable

The complete requirements analysis and architectural design are available in
[`conversational-systems-architecture.pdf`](./conversational-systems-architecture.pdf).
