// Initializes the Firebase app + Auth instance shared by the whole site.
//
// If static/js/firebase-config.js hasn't been created yet (copy it from
// firebase-config.example.js and fill in a real project), this falls back
// to a small local "demo auth" emulator backed by localStorage, so the
// whole site (login/signup, write a post, comment) can be tried without a
// Firebase project. The backend recognizes this in the matching DEMO_MODE
// fallback in app.py. Swap in real firebase-config.js and it upgrades to
// real Firebase Auth automatically - no other file needs to change.
//
// NOTE: the real Firebase SDK is loaded via dynamic import() below, only
// when a real config is present. That keeps demo mode fully self-contained
// (no external request at all) instead of failing outright if the SDK CDN
// is unreachable (offline, corporate firewall, etc).

const hasRealConfig =
    window.firebaseConfig &&
    window.firebaseConfig.apiKey &&
    window.firebaseConfig.apiKey !== "YOUR_API_KEY";

function createDemoAuth() {
    const STORAGE_KEY = "moodtune_demo_user";
    const listeners = new Set();

    function readUser() {
        try {
            const raw = localStorage.getItem(STORAGE_KEY);
            return raw ? JSON.parse(raw) : null;
        } catch {
            return null;
        }
    }

    function writeUser(user) {
        try {
            if (user) localStorage.setItem(STORAGE_KEY, JSON.stringify(user));
            else localStorage.removeItem(STORAGE_KEY);
        } catch {
            // ignore storage failures (private browsing, etc.)
        }
    }

    function withIdToken(user) {
        if (!user) return null;
        return {
            ...user,
            getIdToken: async () =>
                "demo." + btoa(unescape(encodeURIComponent(JSON.stringify(user)))),
        };
    }

    const authObj = {
        get currentUser() {
            return withIdToken(readUser());
        },
    };

    function notify() {
        const user = authObj.currentUser;
        listeners.forEach((cb) => cb(user));
    }

    function demoOnAuthStateChanged(_auth, callback) {
        callback(authObj.currentUser);
        listeners.add(callback);
        return () => listeners.delete(callback);
    }

    async function demoSignIn(_auth, email, _password) {
        const existing = readUser();
        const user =
            existing && existing.email === email
                ? existing
                : { uid: "demo-" + Math.random().toString(36).slice(2, 10), email, displayName: email.split("@")[0] };
        writeUser(user);
        notify();
        return { user: withIdToken(user) };
    }

    async function demoSignUp(_auth, email, _password) {
        const user = { uid: "demo-" + Math.random().toString(36).slice(2, 10), email, displayName: email.split("@")[0] };
        writeUser(user);
        notify();
        return { user: withIdToken(user) };
    }

    async function demoUpdateProfile(user, { displayName }) {
        const stored = readUser();
        if (stored) {
            stored.displayName = displayName;
            writeUser(stored);
            notify();
        }
    }

    async function demoSignOut() {
        writeUser(null);
        notify();
    }

    return {
        auth: authObj,
        onAuthStateChanged: demoOnAuthStateChanged,
        signInWithEmailAndPassword: demoSignIn,
        createUserWithEmailAndPassword: demoSignUp,
        updateProfile: demoUpdateProfile,
        signOut: demoSignOut,
    };
}

async function setup() {
    let moodtuneAuth;

    if (hasRealConfig) {
        const [{ initializeApp }, authModule] = await Promise.all([
            import("https://www.gstatic.com/firebasejs/10.12.2/firebase-app.js"),
            import("https://www.gstatic.com/firebasejs/10.12.2/firebase-auth.js"),
        ]);
        const app = initializeApp(window.firebaseConfig);
        moodtuneAuth = {
            auth: authModule.getAuth(app),
            onAuthStateChanged: authModule.onAuthStateChanged,
            signInWithEmailAndPassword: authModule.signInWithEmailAndPassword,
            createUserWithEmailAndPassword: authModule.createUserWithEmailAndPassword,
            updateProfile: authModule.updateProfile,
            signOut: authModule.signOut,
        };
    } else {
        console.warn(
            "[MoodTune] Firebase가 아직 설정되지 않아 데모 모드(로컬 임시 로그인)로 동작합니다. " +
            "static/js/firebase-config.example.js 를 firebase-config.js 로 복사한 뒤 " +
            "실제 Firebase 프로젝트 값을 채우면 실제 로그인으로 전환됩니다."
        );
        moodtuneAuth = createDemoAuth();
    }

    window.moodtune = { ...moodtuneAuth, isDemo: !hasRealConfig };

    // Let other module scripts (loaded right after this one) know it's ready.
    window.dispatchEvent(new Event("moodtune-firebase-ready"));
}

await setup();
