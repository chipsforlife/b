const section = document.querySelector(".comments");
const postId = section.dataset.postId;
const commentList = document.getElementById("comment-list");
const loginRequired = document.getElementById("comment-login-required");
const commentForm = document.getElementById("comment-form");
const commentText = document.getElementById("comment-text");
const statusEl = document.getElementById("comment-status");

function setStatus(message, isError) {
    statusEl.textContent = message;
    statusEl.className = "status" + (isError ? " error" : "");
}

function appendComment(comment) {
    const emptyMsg = commentList.querySelector(".empty-comments");
    if (emptyMsg) emptyMsg.remove();

    const wrapper = document.createElement("div");
    wrapper.className = "comment";

    const author = document.createElement("span");
    author.className = "comment-author";
    author.textContent = comment.author_name;

    const text = document.createElement("p");
    text.className = "comment-text";
    text.textContent = comment.text;

    wrapper.append(author, text);
    commentList.appendChild(wrapper);
}

function applyAuthState(user) {
    const loggedIn = !!user;
    loginRequired.classList.toggle("hidden", loggedIn);
    commentForm.classList.toggle("hidden", !loggedIn);
}

// auth.js (loaded just before this script) may already have fired its
// state event synchronously, before this listener could be attached - so
// also apply whatever state it already recorded.
applyAuthState(window.moodtune && window.moodtune.currentUser);
window.addEventListener("moodtune-auth-changed", (event) => applyAuthState(event.detail.user));

commentForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const idToken = await window.moodtune.getIdToken();
    if (!idToken) {
        setStatus("You need to log in.", true);
        return;
    }

    const text = commentText.value.trim();
    if (!text) return;

    try {
        const response = await fetch(`/api/posts/${postId}/comments`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${idToken}`,
            },
            body: JSON.stringify({ text }),
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || "Failed to post comment.");
        }

        appendComment(data);
        commentText.value = "";
        setStatus("");
    } catch (error) {
        setStatus(`Error: ${error.message}`, true);
    }
});

// Inline score rendering via OpenSheetMusicDisplay (OSMD), served locally
// from static/vendor so it works offline. OSMD is a UMD bundle loaded by a
// classic <script defer> tag in post_detail.html, which exposes it as
// window.opensheetmusicdisplay. If rendering fails, we hide the viewer and
// the "download .musicxml" link still works.
const scoreViewer = document.getElementById("score-viewer");
if (scoreViewer && scoreViewer.dataset.scoreUrl) {
    (async () => {
        try {
            const OSMD = window.opensheetmusicdisplay && window.opensheetmusicdisplay.OpenSheetMusicDisplay;
            if (!OSMD) throw new Error("OpenSheetMusicDisplay failed to load");
            const response = await fetch(scoreViewer.dataset.scoreUrl);
            if (!response.ok) throw new Error(`Score request failed (status ${response.status})`);
            const xml = await response.text();
            scoreViewer.replaceChildren();
            const osmd = new OSMD(scoreViewer, { autoResize: true, drawTitle: false, backend: "svg" });
            await osmd.load(xml);
            osmd.render();
        } catch (error) {
            scoreViewer.classList.add("hidden");
            console.warn("[MoodTune] Could not render the score preview (download still works):", error);
        }
    })();
}
