const API = window.API_BASE_URL || "http://localhost:8000";

const QUOTES = [
  '"Confidence is the sound of a mind that has already fought this argument once."',
  '"You don\'t win a debate by being right first. You win by being right last."',
  '"The sharpest edge is the one that\'s been tested."',
  '"Every position you haven\'t defended out loud is still just an opinion."',
];

const state = {
  sessionId: crypto.randomUUID(),
  category: null,
  topic: null,
  userStance: null,
  aiStance: null,
  history: [], // {speaker: 'user'|'ai', text}
  researchTimeLeft: 300,
  researchTimer: null,
  debateSeconds: 0,
  debateTimer: null,
  recognizing: false,
};

const $ = (id) => document.getElementById(id);

function showStage(id) {
  document.querySelectorAll(".stage").forEach((s) => s.classList.add("hidden"));
  $(id).classList.remove("hidden");
}

/* ---------------- WELCOME ---------------- */
$("quote-text").textContent = QUOTES[Math.floor(Math.random() * QUOTES.length)];
$("btn-start").onclick = () => {
  loadCategories();
  showStage("stage-category");
};

/* ---------------- CATEGORY ---------------- */
async function loadCategories() {
  const grid = $("category-grid");
  grid.innerHTML = "Loading...";
  try {
    const res = await fetch(`${API}/api/categories`);
    const data = await res.json();
    grid.innerHTML = "";
    data.categories.forEach((cat) => {
      const card = document.createElement("div");
      card.className = "category-card";
      card.textContent = cat.replace("-", " ");
      card.onclick = () => selectCategory(cat);
      grid.appendChild(card);
    });
  } catch (e) {
    grid.innerHTML = "Could not reach backend. Is it running on :8000?";
  }
}

function selectCategory(cat) {
  state.category = cat;
  showStage("stage-wheel");
  spinWheel();
}

/* ---------------- WHEEL ---------------- */
async function spinWheel() {
  const wheel = $("wheel");
  const reveal = $("topic-reveal");
  reveal.textContent = "";
  const spins = 5 + Math.random() * 3;
  wheel.style.transform = `rotate(${spins * 360}deg)`;

  const res = await fetch(`${API}/api/topic/${state.category}`);
  const data = await res.json();
  state.topic = data.topic;

  setTimeout(() => {
    reveal.textContent = state.topic;
    setTimeout(() => {
      $("stance-topic-text").textContent = state.topic;
      showStage("stage-stance");
    }, 1200);
  }, 3600);
}

/* ---------------- STANCE ---------------- */
document.querySelectorAll(".btn-stance").forEach((btn) => {
  btn.onclick = () => {
    state.userStance = btn.dataset.stance;
    state.aiStance = state.userStance === "for" ? "against" : "for";
    showStage("stage-research");
    startResearch();
  };
});

/* ---------------- RESEARCH ---------------- */
function startResearch() {
  state.researchTimeLeft = 300;
  updateResearchTimer();
  state.researchTimer = setInterval(() => {
    state.researchTimeLeft--;
    updateResearchTimer();
    if (state.researchTimeLeft <= 0) finishResearch();
  }, 1000);

  fetch(`${API}/api/research`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: state.sessionId,
      topic: state.topic,
      stance: state.userStance,
    }),
  })
    .then((r) => r.json())
    .then(() => {
      $("ai-thinking").innerHTML = `<div class="pulse-dot" style="background:#5B8C5A"></div> Research brief ready.`;
    })
    .catch(() => {
      $("ai-thinking").textContent = "Research failed — check backend/API key.";
    });
}

function updateResearchTimer() {
  const m = String(Math.floor(state.researchTimeLeft / 60)).padStart(2, "0");
  const s = String(state.researchTimeLeft % 60).padStart(2, "0");
  $("research-timer").textContent = `${m}:${s}`;
}

$("btn-skip-research").onclick = finishResearch;

function finishResearch() {
  clearInterval(state.researchTimer);
  $("debate-topic-label").textContent = state.topic;
  $("user-stance-label").textContent = state.userStance;
  $("ai-stance-label").textContent = state.aiStance;
  showStage("stage-debate");
  startCamera();
  startDebateTimer();
}

/* ---------------- DEBATE ---------------- */
function startDebateTimer() {
  state.debateSeconds = 0;
  state.debateTimer = setInterval(() => {
    state.debateSeconds++;
    const m = String(Math.floor(state.debateSeconds / 60)).padStart(2, "0");
    const s = String(state.debateSeconds % 60).padStart(2, "0");
    $("debate-timer").textContent = `${m}:${s}`;
  }, 1000);
}

async function startCamera() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
    $("user-video").srcObject = stream;
  } catch (e) {
    console.warn("Camera unavailable:", e);
  }
}

function addTranscriptTurn(speaker, text) {
  state.history.push({ speaker, text });
  const div = document.createElement("div");
  div.className = "turn";
  div.innerHTML = `<span class="who ${speaker}">${speaker === "user" ? "You" : "Opponent"}</span>${text}`;
  $("transcript").appendChild(div);
  $("transcript").scrollTop = $("transcript").scrollHeight;
}

/* --- Speech recognition (STT), push-to-talk --- */
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
let recognizer = null;
if (SpeechRecognition) {
  recognizer = new SpeechRecognition();
  recognizer.continuous = false;
  recognizer.interimResults = false;
  recognizer.lang = "en-US";
}

const micBtn = $("btn-mic");
if (!recognizer) {
  micBtn.textContent = "Speech recognition not supported in this browser (use Chrome)";
  micBtn.disabled = true;
} else {
  micBtn.onmousedown = startListening;
  micBtn.ontouchstart = startListening;
  micBtn.onmouseup = stopListeningUI;
  micBtn.ontouchend = stopListeningUI;
}

function startListening() {
  if (state.recognizing) return;
  state.recognizing = true;
  micBtn.classList.add("recording");
  micBtn.textContent = "🎙 Listening... (release when done)";
  $("listening-indicator").classList.add("active");
  recognizer.start();
}

function stopListeningUI() {
  micBtn.classList.remove("recording");
  micBtn.textContent = "🎙 Hold to speak";
}

recognizer && (recognizer.onresult = async (event) => {
  const transcript = event.results[0][0].transcript;
  state.recognizing = false;
  $("listening-indicator").classList.remove("active");
  if (!transcript.trim()) return;
  addTranscriptTurn("user", transcript);
  await getAiResponse(transcript);
});

recognizer && (recognizer.onerror = () => {
  state.recognizing = false;
  $("listening-indicator").classList.remove("active");
  stopListeningUI();
});
recognizer && (recognizer.onend = () => {
  state.recognizing = false;
  $("listening-indicator").classList.remove("active");
});

async function getAiResponse(userMessage) {
  micBtn.disabled = true;
  try {
    const res = await fetch(`${API}/api/debate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: state.sessionId,
        topic: state.topic,
        user_stance: state.userStance,
        history: state.history,
        user_message: userMessage,
      }),
    });
    const data = await res.json();
    addTranscriptTurn("ai", data.text);
    speak(data.text);
  } catch (e) {
    addTranscriptTurn("ai", "(connection error — check backend and API key)");
  } finally {
    micBtn.disabled = false;
  }
}

/* --- Text-to-speech (TTS) + avatar mouth animation --- */
const mouthPaths = {
  closed: "M65 135 Q100 135 135 135",
  small: "M65 133 Q100 145 135 133",
  open: "M62 130 Q100 158 138 130",
  wide: "M60 128 Q100 150 140 128",
};
let mouthInterval = null;

function speak(text) {
  const utter = new SpeechSynthesisUtterance(text);
  utter.rate = 1.02;
  utter.pitch = 0.92;

  utter.onstart = () => {
    let shapes = Object.values(mouthPaths).filter((s) => s !== mouthPaths.closed);
    mouthInterval = setInterval(() => {
      const shape = shapes[Math.floor(Math.random() * shapes.length)];
      $("avatar-mouth").setAttribute("d", shape);
    }, 110);
  };
  utter.onend = () => {
    clearInterval(mouthInterval);
    $("avatar-mouth").setAttribute("d", mouthPaths.closed);
  };

  speechSynthesis.speak(utter);
}

/* ---------------- END DEBATE / SCORECARD ---------------- */
$("btn-end-debate").onclick = async () => {
  clearInterval(state.debateTimer);
  speechSynthesis.cancel();
  showStage("stage-scorecard");
  $("scorecard-box").textContent = "Generating your scorecard...";
  try {
    const res = await fetch(`${API}/api/scorecard`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ topic: state.topic, history: state.history }),
    });
    const data = await res.json();
    $("scorecard-box").textContent = data.scorecard;
  } catch (e) {
    $("scorecard-box").textContent = "Could not generate scorecard — check backend and API key.";
  }
};

$("btn-restart").onclick = () => {
  Object.assign(state, {
    sessionId: crypto.randomUUID(),
    category: null,
    topic: null,
    userStance: null,
    aiStance: null,
    history: [],
  });
  $("transcript").innerHTML = "";
  $("quote-text").textContent = QUOTES[Math.floor(Math.random() * QUOTES.length)];
  showStage("stage-welcome");
};
