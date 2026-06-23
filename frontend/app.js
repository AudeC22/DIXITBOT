const API_URL = "/api/ask";

const form = document.getElementById("chatForm");
const input = document.getElementById("userInput");
const messagesEl = document.getElementById("messages");
const statusEl = document.getElementById("status");
const sendBtn = document.getElementById("sendBtn");
const clearBtn = document.getElementById("clearBtn");
const shareBtn = document.getElementById("shareBtn");
const yearEl = document.getElementById("year");

const chipButtons = document.querySelectorAll(".chip");

let chatHistory = [
  {
    role: "bot",
    text:
      "Bonjour ! Donne-moi ton sujet de recherche (problématique, mots-clés, contraintes), et je te propose une synthèse structurée avec citations.",
  },
];

function scrollToBottom() {
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function setLoading(isLoading, text = "") {
  sendBtn.disabled = isLoading;
  input.disabled = isLoading;
  statusEl.textContent = text;
}

function addMessage({ role, text, persist = true }) {
  const wrapper = document.createElement("div");
  wrapper.className = `msg ${role === "user" ? "msg-user" : "msg-bot"}`;

  const meta = document.createElement("div");
  meta.className = "msg-meta";
  meta.textContent = role === "user" ? "Vous" : "DIXIT";

  const bubble = document.createElement("div");
  bubble.className = "msg-bubble";
  bubble.textContent = text;

  wrapper.appendChild(meta);
  wrapper.appendChild(bubble);
  messagesEl.appendChild(wrapper);

  if (persist) chatHistory.push({ role, text });

  scrollToBottom();
}

function safeTrim(value) {
  return (value || "").replace(/\s+/g, " ").trim();
}

async function sendToBackend(userText) {
  const payload = { question: userText };

  const res = await fetch(API_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const raw = await res.text().catch(() => "");
    throw new Error(`Erreur API (${res.status}) ${raw ? `— ${raw}` : ""}`);
  }

  const data = await res.json();
  const reply = data.answer || data.reply || data.message || data.output;

  if (!reply || typeof reply !== "string") {
    throw new Error("Réponse backend invalide (champ answer/reply/message/output manquant).");
  }

  return reply;
}

async function handleSend(text) {
  const userText = safeTrim(text);
  if (!userText) return;

  addMessage({ role: "user", text: userText });
  input.value = "";

  setLoading(true, "Analyse en cours…");
  try {
    const reply = await sendToBackend(userText);
    addMessage({ role: "bot", text: reply });
    setLoading(false, "");
  } catch (err) {
    addMessage({
      role: "bot",
      text:
        "Je n’arrive pas à joindre le backend. Vérifie l’URL API dans app.js et que le serveur est démarré.\n\n" +
        `Détail : ${err.message}`,
    });
    setLoading(false, "Erreur — backend indisponible ou réponse invalide.");
  }
}

function buildEmailBody() {
  const lines = [];
  lines.push("Historique de recherche — DIXIT BOT");
  lines.push("");
  lines.push("Sources: arXiv + Semantic Scholar");
  lines.push("");
  lines.push("— Conversation —");
  lines.push("");

  chatHistory.forEach((m) => {
    const who = m.role === "user" ? "Vous" : "DIXIT";
    lines.push(`${who}: ${m.text}`);
    lines.push("");
  });

  lines.push("— Fin —");
  return lines.join("\n");
}

function openEmailClient() {
  const subject = "DIXIT BOT — Historique de recherche";
  const body = buildEmailBody();
  const mailto = `mailto:?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
  window.location.href = mailto;
}

form.addEventListener("submit", (e) => {
  e.preventDefault();
  handleSend(input.value);
});

clearBtn.addEventListener("click", () => {
  const children = Array.from(messagesEl.children);
  children.slice(1).forEach((node) => node.remove());

  chatHistory = [chatHistory[0]];
  statusEl.textContent = "";
  input.focus();
});

shareBtn.addEventListener("click", () => {
  openEmailClient();
});

chipButtons.forEach((btn) => {
  btn.addEventListener("click", () => {
    const prompt = btn.getAttribute("data-prompt") || "";
    input.value = prompt;
    input.focus();
    handleSend(prompt);
  });
});

input.addEventListener("keydown", (e) => {
  const isMac = navigator.platform.toLowerCase().includes("mac");
  const combo = isMac ? e.metaKey : e.ctrlKey;
  if (combo && e.key === "Enter") {
    e.preventDefault();
    handleSend(input.value);
  }
});

if (yearEl) yearEl.textContent = String(new Date().getFullYear());

const healthBtn = document.getElementById('health-btn');
const askBtn = document.getElementById('ask-btn');
const queryInput = document.getElementById('query-input');
const resultDiv = document.getElementById('result');

healthBtn.addEventListener('click', async () => {
  try {
    const response = await fetch('/api/health');
    const data = await response.json();
    resultDiv.textContent = JSON.stringify(data, null, 2);
  } catch (error) {
    resultDiv.textContent = 'Erreur: ' + error.message;
  }
});

askBtn.addEventListener('click', async () => {
  const query = queryInput.value;
  if (!query) return;
  try {
    const response = await fetch('/api/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query }),
    });
    const data = await response.json();
    resultDiv.textContent = JSON.stringify(data, null, 2);
  } catch (error) {
    resultDiv.textContent = 'Erreur: ' + error.message;
  }
});
