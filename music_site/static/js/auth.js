// Shared header auth state + helpers used on every page.
const navAuth = document.getElementById("nav-auth");

function renderNav(user) {
    if (!navAuth) return;
    navAuth.innerHTML = "";

    if (user) {
        const name = document.createElement("span");
        name.className = "nav-username";
        name.textContent = user.displayName || user.email || "User";

        const newPostLink = document.createElement("a");
        newPostLink.href = "/new";
        newPostLink.className = "nav-link";
        newPostLink.textContent = "New post";

        const logoutBtn = document.createElement("button");
        logoutBtn.className = "nav-btn";
        logoutBtn.textContent = "Log out";
        logoutBtn.addEventListener("click", async () => {
            await window.moodtune.signOut(window.moodtune.auth);
            window.location.href = "/";
        });

        navAuth.append(newPostLink, name, logoutBtn);
    } else {
        const loginLink = document.createElement("a");
        loginLink.href = "/login";
        loginLink.className = "nav-link";
        loginLink.textContent = "Log in / Sign up";
        navAuth.append(loginLink);
    }
}

// Other page scripts (new_post.js, post_detail.js) are loaded after this
// one but may attach their "moodtune-auth-changed" listener too late to
// catch this first, synchronous firing - so the current user is also kept
// on window.moodtune.currentUser for them to read directly on init.
window.moodtune = window.moodtune || {};

if (window.moodtune.auth) {
    window.moodtune.onAuthStateChanged(window.moodtune.auth, (user) => {
        window.moodtune.currentUser = user;
        renderNav(user);
        window.dispatchEvent(new CustomEvent("moodtune-auth-changed", { detail: { user } }));
    });
} else {
    renderNav(null);
}

// Helper other pages can await to get a fresh ID token (or null if logged out).
window.moodtune.getIdToken = async function getIdToken() {
    const auth = window.moodtune.auth;
    if (!auth || !auth.currentUser) return null;
    return auth.currentUser.getIdToken();
};
