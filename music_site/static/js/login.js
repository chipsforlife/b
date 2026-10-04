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
        "auth/invalid-email": "Invalid email address.",
        "auth/user-not-found": "No account found with that email.",
        "auth/wrong-password": "Incorrect password.",
        "auth/invalid-credential": "Incorrect email or password.",
        "auth/email-already-in-use": "That email is already registered.",
        "auth/weak-password": "Password must be at least 6 characters.",
    };
    return map[code] || (error && error.message) || "An unknown error occurred.";
}

function requireFirebase() {
    if (!window.moodtune || !window.moodtune.auth) {
        setStatus(
            "Firebase setup required. Please fill in static/js/firebase-config.js.",
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
    setStatus("Logging in...");
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
    setStatus("Creating account...");
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
