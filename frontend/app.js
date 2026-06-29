const API_URL = "/api/ask";

const form = document.getElementById("chatForm");
const input = document.getElementById("userInput");
const messagesEl = document.getElementById("messages");
const statusEl = document.getElementById("status");
const sendBtn = document.getElementById("sendBtn");
const clearBtn = document.getElementById("clearBtn");
const shareBtn = document.getElementById("shareBtn");
const sendEmailBtn = document.getElementById("sendEmailBtn");
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

async function handleSend(text) {
  const userText = safeTrim(text);
  if (!userText) return;

  addMessage({ role: "user", text: userText });
  input.value = "";

  setLoading(true, "Analyse en cours…");

  // Étape 1 : appel réseau — si fetch échoue, c’est une vraie erreur de connexion
  let res;
  try {
    res = await fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: userText }),
    });
  } catch (networkErr) {
    addMessage({
      role: "bot",
      text:
        "Je n’arrive pas à joindre le backend. Vérifie l’URL API dans app.js et que le serveur est démarré.\n\n" +
        `Détail : ${networkErr.message}`,
    });
    setLoading(false, "Erreur — backend indisponible ou réponse invalide.");
    return;
  }

  // Étape 2 : le backend a répondu, mais avec un code d’erreur (ex: 503)
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    const detail = data.detail || `Code HTTP ${res.status}`;
    addMessage({ role: "bot", text: `Le backend a renvoyé une erreur.\n\nDétail : ${detail}` });
    setLoading(false, "Erreur — le backend a renvoyé une erreur.");
    return;
  }

  // Étape 3 : lecture et affichage de la réponse
  try {
    const data = await res.json();
    const reply = data.answer || data.reply || data.message || data.output;
    if (!reply || typeof reply !== "string") {
      throw new Error("Réponse backend invalide (champ answer/reply/message/output manquant).");
    }
    addMessage({ role: "bot", text: reply });
    setLoading(false, "");
  } catch (parseErr) {
    addMessage({ role: "bot", text: "Réponse backend invalide.\n\nDétail : " + parseErr.message });
    setLoading(false, "Erreur — réponse invalide.");
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

function buildConversationHistory() {
  // Reprend la structure déjà utilisée pour chatHistory (role + text),
  // et l'adapte au format attendu par le backend (role + content + timestamp).
  const history = [];
  for (const message of chatHistory) {
    history.push({
      role: message.role,
      content: message.text,
      timestamp: new Date().toISOString(),
    });
  }
  return history;
}

async function sendEmailToBackend(payload) {
  const res = await fetch("/api/send-email", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const raw = await res.text().catch(() => "");
    throw new Error(`Erreur API (${res.status}) ${raw ? `— ${raw}` : ""}`);
  }

  return res.json();
}

async function handleSendHistoryByEmail() {
  const recipientEmail = window.prompt("Adresse email du destinataire :");
  if (!recipientEmail) return;

  const payload = {
    recipient_email: recipientEmail,
    subject: "Historique de recherche — DIXIT BOT",
    conversation_history: buildConversationHistory(),
  };

  try {
    await sendEmailToBackend(payload);
    addMessage({ role: "bot", text: "Email envoyé avec succès." });
  } catch (err) {
    addMessage({
      role: "bot",
      text: "Je n’ai pas pu envoyer l’email.\n\n" + `Détail : ${err.message}`,
    });
  }
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

sendEmailBtn.addEventListener("click", () => {
  handleSendHistoryByEmail();
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
