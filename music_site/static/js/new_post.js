const form = document.getElementById("generate-form");
const loginRequired = document.getElementById("login-required");
const titleInput = document.getElementById("title");
const promptInput = document.getElementById("prompt");
const durationInput = document.getElementById("duration");
const durationValue = document.getElementById("duration-value");
const genreButtons = document.querySelectorAll("#genre-presets .style-btn");
const moodSelect = document.getElementById("mood");
const tempoButtons = document.querySelectorAll("#tempo-presets .style-btn");
const statusEl = document.getElementById("status");
const generateBtn = document.getElementById("generate-btn");
const previewEl = document.getElementById("preview");
const previewAudio = document.getElementById("preview-audio");

let selectedGenre = "";
let selectedTempo = document.querySelector("#tempo-presets .style-btn.active")?.dataset.tempo || "";

genreButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
        genreButtons.forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        selectedGenre = btn.dataset.genre || "";
    });
});

tempoButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
        tempoButtons.forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        selectedTempo = btn.dataset.tempo || "";
    });
});

durationInput.addEventListener("input", () => {
    durationValue.textContent = durationInput.value;
});

function setStatus(message, isError) {
    statusEl.textContent = message;
    statusEl.className = "status" + (isError ? " error" : "");
}

function applyAuthState(user) {
    const loggedIn = !!user;
    loginRequired.classList.toggle("hidden", loggedIn);
    form.classList.toggle("hidden", !loggedIn);
}

// auth.js (loaded just before this script) may already have fired its
// state event synchronously, before this listener could be attached - so
// also apply whatever state it already recorded.
applyAuthState(window.moodtune && window.moodtune.currentUser);
window.addEventListener("moodtune-auth-changed", (event) => applyAuthState(event.detail.user));

form.addEventListener("submit", async (event) => {
    event.preventDefault();

    const idToken = await window.moodtune.getIdToken();
    if (!idToken) {
        setStatus("로그인이 필요합니다.", true);
        return;
    }

    if (!moodSelect.value) {
        setStatus("오케스트라 악보의 무드를 선택해주세요.", true);
        moodSelect.focus();
        return;
    }

    generateBtn.disabled = true;
    generateBtn.textContent = "생성 중...";
    setStatus("AI가 음악과 악보를 만들고 있어요 — 최대 1~2분 정도 걸릴 수 있습니다.");
    previewEl.classList.add("hidden");

    try {
        const response = await fetch("/api/posts", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${idToken}`,
            },
            body: JSON.stringify({
                title: titleInput.value.trim(),
                prompt: promptInput.value.trim(),
                genre: selectedGenre,
                duration: Number(durationInput.value),
                mood: moodSelect.value,
                tempo: selectedTempo,
            }),
        });

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || "음악 생성에 실패했습니다.");
        }

        setStatus("");
        previewEl.classList.remove("hidden");
        previewAudio.src = data.audio_url;
        setTimeout(() => {
            window.location.href = `/post/${data.id}`;
        }, 1500);
    } catch (error) {
        setStatus(`오류: ${error.message}`, true);
    } finally {
        generateBtn.disabled = false;
        generateBtn.textContent = "🎵 음악 + 악보 생성하기";
    }
});
