"use strict";

/**
 * Policy Consultant demo UI.
 *
 * Talks only to this same app's existing endpoints (GET /api/profiles,
 * POST /api/ask) — no new backend logic lives here, this file is purely
 * presentation. Every piece of text that could come from the model or
 * from a policy document (answers, citation fragments) is rendered via
 * textContent, never innerHTML, so nothing in that content is ever
 * interpreted as markup.
 */

const profileSelect = document.getElementById("profile-select");
const chatLog = document.getElementById("chat-log");
const statusMessage = document.getElementById("status-message");
const askForm = document.getElementById("ask-form");
const questionInput = document.getElementById("question-input");
const sendButton = document.getElementById("send-button");

let isSubmitting = false;

// Bumped every time the profile changes, so an answer from a request
// that was still in flight under the previous profile can be told
// apart from the current one and silently dropped instead of being
// appended to a chat log that has already moved on to a different RLS
// context.
let activeGeneration = 0;

function setStatus(text, isError) {
  statusMessage.textContent = text;
  statusMessage.classList.toggle("is-error", Boolean(isError));
}

function createElement(tag, className, text) {
  const element = document.createElement(tag);
  if (className) {
    element.className = className;
  }
  if (text !== undefined) {
    element.textContent = text;
  }
  return element;
}

function appendUserMessage(question) {
  const bubble = createElement("div", "message message-user");
  bubble.appendChild(createElement("p", "message-label", "You"));
  bubble.appendChild(createElement("p", "message-text", question));
  chatLog.appendChild(bubble);
  chatLog.scrollTop = chatLog.scrollHeight;
}

function citationLabel(citation) {
  const section = citation.section_path && citation.section_path.length
    ? citation.section_path.join(" / ")
    : null;
  const parts = [citation.document_id, "v" + citation.version];
  if (section) {
    parts.push(section);
  }
  return parts.join(" — ");
}

function appendCitations(container, citations) {
  if (!citations || citations.length === 0) {
    return;
  }

  const details = createElement("details", "citations");
  details.appendChild(
    createElement("summary", null, "Sources (" + citations.length + ")")
  );

  citations.forEach((citation) => {
    const item = createElement("div", "citation");
    item.appendChild(createElement("p", "citation-source", citationLabel(citation)));
    item.appendChild(createElement("p", "citation-text", citation.text));
    details.appendChild(item);
  });

  container.appendChild(details);
}

function appendAssistantMessage(answer, modifierClass, label, citations) {
  const bubble = createElement("div", "message message-assistant");
  if (modifierClass) {
    bubble.classList.add(modifierClass);
  }
  bubble.appendChild(createElement("p", "message-label", label));
  bubble.appendChild(createElement("p", "message-text", answer));
  appendCitations(bubble, citations);
  chatLog.appendChild(bubble);
  chatLog.scrollTop = chatLog.scrollHeight;
}

async function loadProfiles() {
  try {
    const response = await fetch("/api/profiles");
    if (!response.ok) {
      throw new Error("Failed to load profiles");
    }
    const profiles = await response.json();

    profileSelect.textContent = "";
    profiles.forEach((profile) => {
      const option = createElement("option", null, profile.label);
      option.value = profile.id;
      profileSelect.appendChild(option);
    });
    profileSelect.disabled = false;
  } catch (error) {
    setStatus("Could not load demo profiles. Please reload the page.", true);
  }
}

/** FastAPI's default error body is {"detail": "..."} for a plain
 * HTTPException, or {"detail": [...]} (a list of validation issues)
 * for a 422 — this only ever surfaces a short, generic message to the
 * user either way, never the raw structure. */
async function extractErrorMessage(response) {
  try {
    const body = await response.json();
    if (typeof body.detail === "string") {
      return body.detail;
    }
  } catch (error) {
    // Response body wasn't JSON — fall through to the generic message.
  }
  if (response.status === 422) {
    return "That question could not be submitted. Please check it and try again.";
  }
  return "Something went wrong while generating an answer. Please try again.";
}

async function askQuestion(profileId, question) {
  const response = await fetch("/api/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ profile_id: profileId, question: question }),
  });

  if (!response.ok) {
    const message = await extractErrorMessage(response);
    const error = new Error(message);
    error.isUserFacing = true;
    throw error;
  }

  return response.json();
}

async function handleSubmit(event) {
  event.preventDefault();

  if (isSubmitting) {
    return;
  }

  const profileId = profileSelect.value;
  const question = questionInput.value.trim();
  if (!profileId || !question) {
    setStatus("Choose a profile and enter a question.", true);
    return;
  }

  const generationAtSubmit = activeGeneration;
  isSubmitting = true;
  sendButton.disabled = true;
  sendButton.textContent = "Thinking…";
  setStatus("Thinking…", false);

  appendUserMessage(question);
  questionInput.value = "";

  try {
    const result = await askQuestion(profileId, question);
    if (generationAtSubmit !== activeGeneration) {
      // The profile changed while this request was in flight; the
      // chat has already been cleared for the new profile, so this
      // now-stale answer must never appear in it.
      return;
    }
    if (result.abstained) {
      appendAssistantMessage(result.answer, "abstained", "Policy Consultant — no answer found", result.citations);
    } else {
      appendAssistantMessage(result.answer, null, "Policy Consultant", result.citations);
    }
    setStatus("", false);
  } catch (error) {
    if (generationAtSubmit !== activeGeneration) {
      return;
    }
    appendAssistantMessage(error.message, "error", "Policy Consultant — error", null);
    setStatus("The last question could not be answered.", true);
  } finally {
    // Only resets the UI if nothing has reset it already (see
    // handleProfileChange below) — otherwise a stale request finishing
    // late could re-enable a button or clear a status message that no
    // longer belongs to it.
    if (generationAtSubmit === activeGeneration) {
      isSubmitting = false;
      sendButton.disabled = false;
      sendButton.textContent = "Send";
      questionInput.focus();
    }
  }
}

function handleProfileChange() {
  activeGeneration++;
  chatLog.textContent = "";
  setStatus("", false);
  isSubmitting = false;
  sendButton.disabled = false;
  sendButton.textContent = "Send";
}

function setupExampleQuestions() {
  document.querySelectorAll(".example-question-button").forEach((button) => {
    button.addEventListener("click", () => {
      questionInput.value = button.dataset.question;
      questionInput.focus();
    });
  });
}

askForm.addEventListener("submit", handleSubmit);
profileSelect.addEventListener("change", handleProfileChange);
setupExampleQuestions();
loadProfiles();
