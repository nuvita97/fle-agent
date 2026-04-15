/* =========================================================
   FLE-agent — Exercise page JavaScript
   Features: MCQ selection, timer, scoring, hints,
             vocab toggle, score history, confetti
   ========================================================= */

// ── State ──────────────────────────────────────────────────
const TOTAL_Q   = QUESTIONS.length;  // injected by Jinja
let answered    = 0;
let submitted   = false;
let timerSecs   = 10 * 60;
let timerHandle = null;

// ── DOM helpers ────────────────────────────────────────────
const $  = (sel, ctx = document) => ctx.querySelector(sel);
const $$ = (sel, ctx = document) => [...ctx.querySelectorAll(sel)];

// ── On load ─────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  initChoices();
  initTimer();
  initSubmit();
  initRestart();
  initVocabToggle();
  loadHistory();
});

// ── Choice selection ────────────────────────────────────────
function initChoices() {
  $$(".choice").forEach(choice => {
    choice.addEventListener("click", () => {
      if (submitted) return;

      const block = choice.closest(".question-block");
      const wasAnswered = !!$(".choice.selected", block);

      // Deselect all in this block
      $$(".choice", block).forEach(c => c.classList.remove("selected"));
      choice.classList.add("selected");
      choice.querySelector("input").checked = true;

      if (!wasAnswered) {
        answered++;
        updateProgress();
      }
    });
  });
}

// ── Progress bar ────────────────────────────────────────────
function updateProgress() {
  const pct = (answered / TOTAL_Q) * 100;
  $("#progress-fill").style.width = pct + "%";
  $("#progress-label").textContent = UI.progress_label
    .replace("{answered}", answered)
    .replace("{total}", TOTAL_Q);
}

// ── Timer ────────────────────────────────────────────────────
function initTimer() {
  renderTimer();
  timerHandle = setInterval(() => {
    timerSecs--;
    renderTimer();
    if (timerSecs <= 60) $("#timer").classList.add("warning");
    if (timerSecs <= 0) {
      clearInterval(timerHandle);
      submitAnswers(true);
    }
  }, 1000);
}

function renderTimer() {
  const m = Math.floor(Math.max(0, timerSecs) / 60);
  const s = Math.max(0, timerSecs) % 60;
  $("#timer").textContent = `${m}:${String(s).padStart(2, "0")}`;
}

// ── Submit ───────────────────────────────────────────────────
function initSubmit() {
  $("#submit-btn").addEventListener("click", () => submitAnswers(false));
}

function submitAnswers(timeUp = false) {
  if (submitted) return;
  submitted = true;
  clearInterval(timerHandle);

  let correct = 0;

  QUESTIONS.forEach((q, i) => {
    const block      = $(`#q-block-${i}`);
    const choices    = $$(".choice", block);
    const selected   = $(".choice.selected", block);
    const userAnswer = selected ? selected.dataset.letter : null;

    // Mark all choices
    choices.forEach(c => {
      c.style.cursor = "default";
      const letter = c.dataset.letter;
      if (letter === q.answer) {
        c.classList.add("correct");
      } else if (letter === userAnswer && userAnswer !== q.answer) {
        c.classList.add("wrong");
      }
    });

    // Show explanation
    if (q.explanation) {
      const expDiv = $(`#explanation-${i}`);
      expDiv.innerHTML = `<strong>${UI.explanation_label}&nbsp;:</strong> ${q.explanation}`;
      expDiv.style.display = "block";
    }

    if (userAnswer === q.answer) correct++;
  });

  const finalScore = correct;

  // Show score banner
  const banner = $("#score-banner");
  banner.style.display = "block";
  $("#score-number").textContent = `${finalScore % 1 === 0 ? finalScore : finalScore.toFixed(1)} / ${TOTAL_Q}`;
  const msgs = {
    perfect : UI.msg_perfect,
    great   : UI.msg_great,
    good    : UI.msg_good,
    ok      : UI.msg_ok,
    low     : UI.msg_low,
  };
  const pct = finalScore / TOTAL_Q;
  const msgKey = pct === 1 ? "perfect" : pct >= 0.8 ? "great" : pct >= 0.6 ? "good" : pct >= 0.4 ? "ok" : "low";
  if (timeUp) {
    $("#score-msg").textContent = `${UI.time_up} ${msgs[msgKey]}`;
  } else {
    $("#score-msg").textContent = msgs[msgKey];
  }

  // Confetti on perfect score
  if (correct === TOTAL_Q && typeof confetti !== "undefined") {
    confetti({ particleCount: 150, spread: 80, origin: { y: 0.6 } });
    setTimeout(() => confetti({ particleCount: 80, spread: 120, origin: { y: 0.5 } }), 600);
  }

  // Hide submit, show restart
  $("#submit-btn").style.display = "none";
  $("#restart-btn").style.display = "inline-flex";

  // Save to history
  saveHistory(finalScore);
  renderHistory();

  // Scroll to banner
  banner.scrollIntoView({ behavior: "smooth", block: "center" });

  // Track submission (fire-and-forget)
  fetch("/track", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ event_type: "submit_answers", level: LEVEL, topic: TOPIC }),
  }).catch(() => {});
}

// ── Restart ──────────────────────────────────────────────────
function initRestart() {
  $("#restart-btn").addEventListener("click", () => {
    // Reset state
    submitted = false;
    answered  = 0;
    timerSecs = 10 * 60;

    // Reset UI
    $$(".choice").forEach(c => {
      c.classList.remove("selected", "correct", "wrong");
      c.style.opacity = "1";
      c.style.cursor  = "pointer";
      c.querySelector("input").checked = false;
    });
    $$(".explanation-msg").forEach(d => { d.style.display = "none"; d.innerHTML = ""; });

    $("#progress-fill").style.width = "0%";
    $("#progress-label").textContent = UI.progress_label.replace("{answered}", 0).replace("{total}", TOTAL_Q);
    $("#score-banner").style.display = "none";
    $("#timer").classList.remove("warning");
    $("#submit-btn").style.display = "inline-flex";
    $("#restart-btn").style.display = "none";

    renderTimer();
    timerHandle = setInterval(() => {
      timerSecs--;
      renderTimer();
      if (timerSecs <= 60) $("#timer").classList.add("warning");
      if (timerSecs <= 0) { clearInterval(timerHandle); submitAnswers(true); }
    }, 1000);

    window.scrollTo({ top: $("#section-questions").offsetTop - 20, behavior: "smooth" });
  });
}

// ── Vocabulary toggle ────────────────────────────────────────
function initVocabToggle() {
  const btn     = $("#vocab-toggle");
  const content = $("#vocab-content");
  btn.addEventListener("click", () => {
    const open = content.style.display !== "none";
    content.style.display = open ? "none" : "block";
    btn.textContent = open ? UI.show_vocab : UI.hide_vocab;
  });
}

// ── Score history (localStorage) ─────────────────────────────
const HISTORY_KEY = "fle_score_history";

function saveHistory(score) {
  const history = loadRawHistory();
  history.unshift({ score, total: TOTAL_Q, date: new Date().toLocaleString("fr-FR") });
  localStorage.setItem(HISTORY_KEY, JSON.stringify(history.slice(0, 5)));
}

function loadRawHistory() {
  try { return JSON.parse(localStorage.getItem(HISTORY_KEY)) || []; }
  catch { return []; }
}

function loadHistory() {
  renderHistory();
}

function renderHistory() {
  const history = loadRawHistory();
  const panel   = $("#history-panel");
  const list    = $("#history-list");
  if (!history.length) return;
  panel.style.display = "block";
  list.innerHTML = history.map(h =>
    `<li>🗓 ${h.date} &mdash; <strong>${h.score}/${h.total}</strong></li>`
  ).join("");
}
