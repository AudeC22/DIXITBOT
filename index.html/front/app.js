// URL du backend (Imène côté projet) — API /chat
const BACKEND_URL = "http://localhost:8000/chat";

// Récupération des éléments HTML
const messagesEl = document.getElementById("messages");
const sourcesListEl = document.getElementById("sourcesList");
const statusEl = document.getElementById("status");

const form = document.getElementById("chatForm");
const input = document.getElementById("input");
const sendBtn = document.getElementById("sendBtn");
const clearBtn = document.getElementById("clearBtn");

// Ajoute une bulle dans le chat
function addMessage(text, who) {
  const div = document.createElement("div");
  div.className = `msg ${who}`;
  div.textContent = text;
  messagesEl.appendChild(div);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

// Affiche la liste de sources (si le backend en fournit)
function renderSources(sources) {
  sourcesListEl.innerHTML = "";

  if (!sources || sources.length === 0) {
    sourcesListEl.innerHTML = `<p class="muted">Aucune source affichée pour le moment.</p>`;
    return;
  }

  for (const s of sources) {
    const item = document.createElement("div");
    item.className = "source-item";

    const title = document.createElement("p");
    title.className = "source-title";
    title.textContent = s.title || "Source";

    const meta = document.createElement("p");
    meta.className = "source-meta";
    meta.textContent = s.url ? s.url : (s.note || "");

    item.appendChild(title);
    item.appendChild(meta);
    sourcesListEl.appendChild(item);
  }
}

// Active / désactive l'UI pendant le chargement
function setLoading(isLoading) {
  sendBtn.disabled = isLoading;
  input.disabled = isLoading;
}

// Bouton “Effacer”
clearBtn.addEventListener("click", () => {
  messagesEl.innerHTML = "";
  renderSources([]);
  addMessage("Bonjour ! Pose ta question de recherche 👇", "bot");
});

// Test simple : afficher un message d’accueil
addMessage("Bonjour ! Je suis Dixit. Quelle est ta question de recherche ?", "bot");
renderSources([]);

// Quand l’utilisateur envoie un message
form.addEventListener("submit", async (e) => {
  e.preventDefault();

  const text = input.value.trim();
  if (!text) return;

  addMessage(text, "user");
  input.value = "";

  // placeholder “…” pendant que le backend répond
  addMessage("…", "bot");
  const placeholder = messagesEl.lastChild;

  setLoading(true);
  statusEl.textContent = "Backend : requête en cours…";

  try {
    const res = await fetch(BACKEND_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text })
    });

    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    const data = await res.json();

    // Réponse principale attendue
    placeholder.textContent = data.answer ?? "(Réponse vide)";

    // BONUS (prévu pour votre projet “réponses citées”):
    // Si votre backend renvoie un champ "sources", on l’affiche.
    // Exemple attendu :
    // { answer: "...", sources: [{title:"...", url:"..."}] }
    renderSources(data.sources || []);

    statusEl.textContent = "Backend : OK ✅";
  } catch (err) {
    placeholder.textContent =
      "❌ Impossible de contacter le backend. Vérifie qu’il tourne sur http://localhost:8000";
    statusEl.textContent = "Backend : indisponible ❌";
    renderSources([]);
  } finally {
    setLoading(false);
    input.focus();
  }
});
