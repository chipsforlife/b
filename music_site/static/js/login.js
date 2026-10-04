const tabButtons = document.querySelectorAll(".tab-btn");
const loginForm = document.getElementById("login-form");
const signupForm = document.getElementById("signup-form");
const statusEl = document.getElementById("auth-status");

tabButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
        tabButtons.forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        const isLogin = btn.dataset.tab === "login";
        loginForm.classList.toggle("hidden", !isLogin);
        signupForm.classList.toggle("hidden", isLogin);
        statusEl.textContent = "";
    });
});

function setStatus(message, isError) {
    statusEl.textContent = message;
    statusEl.className = "status" + (isError ? " error" : "");
}

function friendlyError(error) {
    const code = error && error.code;
    const map = {
        "auth/invalid-email": "이메일 형식이 올바르지 않습니다.",
        "auth/user-not-found": "존재하지 않는 계정입니다.",
        "auth/wrong-password": "비밀번호가 일치하지 않습니다.",
        "auth/invalid-credential": "이메일 또는 비밀번호가 일치하지 않습니다.",
        "auth/email-already-in-use": "이미 가입된 이메일입니다.",
        "auth/weak-password": "비밀번호는 6자 이상이어야 합니다.",
    };
    return map[code] || (error && error.message) || "알 수 없는 오류가 발생했습니다.";
}

function requireFirebase() {
    if (!window.moodtune || !window.moodtune.auth) {
        setStatus(
            "Firebase 설정이 필요합니다. static/js/firebase-config.js 파일을 채워주세요.",
            true
        );
        return false;
    }
    return true;
}

loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!requireFirebase()) return;

    const { email, password } = Object.fromEntries(new FormData(loginForm));
    setStatus("로그인 중...");
    try {
        await window.moodtune.signInWithEmailAndPassword(window.moodtune.auth, email, password);
        window.location.href = "/";
    } catch (error) {
        setStatus(friendlyError(error), true);
    }
});

signupForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!requireFirebase()) return;

    const { name, email, password } = Object.fromEntries(new FormData(signupForm));
    setStatus("가입 처리 중...");
    try {
        const credential = await window.moodtune.createUserWithEmailAndPassword(
            window.moodtune.auth,
            email,
            password
        );
        await window.moodtune.updateProfile(credential.user, { displayName: name });
        window.location.href = "/";
    } catch (error) {
        setStatus(friendlyError(error), true);
    }
});
