const form = document.getElementById("generate-form");
const promptInput = document.getElementById("prompt");
const sizeSelect = document.getElementById("size");
const statusEl = document.getElementById("status");
const resultEl = document.getElementById("result");
const generateBtn = document.getElementById("generate-btn");
const styleButtons = document.querySelectorAll(".style-btn");

let selectedStyle = { label: "None", suffix: "" };

styleButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
        styleButtons.forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        selectedStyle = { label: btn.textContent.trim(), suffix: btn.dataset.suffix || "" };
    });
});

form.addEventListener("submit", async (event) => {
    event.preventDefault();

    const basePrompt = promptInput.value.trim();
    if (!basePrompt) return;

    const finalPrompt = selectedStyle.suffix
        ? `${basePrompt}, ${selectedStyle.suffix}`
        : basePrompt;

    generateBtn.disabled = true;
    generateBtn.textContent = "Generating...";
    statusEl.textContent = "Generating your image — this can take up to 30 seconds.";
    statusEl.className = "status loading";

    try {
        const response = await fetch("/generate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ prompt: finalPrompt, size: sizeSelect.value }),
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Something went wrong.");
        }

        statusEl.textContent = "";
        statusEl.className = "status";
        addImageCard(data.image, basePrompt, selectedStyle.label);
    } catch (error) {
        statusEl.textContent = `Error: ${error.message}`;
        statusEl.className = "status error";
    } finally {
        generateBtn.disabled = false;
        generateBtn.textContent = "Generate";
    }
});

function addImageCard(imageDataUrl, prompt, styleLabel) {
    const figure = document.createElement("figure");
    figure.className = "image-card";

    const img = document.createElement("img");
    img.src = imageDataUrl;
    img.alt = prompt;

    const caption = document.createElement("figcaption");

    const promptText = document.createElement("span");
    promptText.textContent = prompt;
    caption.appendChild(promptText);

    if (styleLabel && styleLabel !== "None") {
        const badge = document.createElement("span");
        badge.className = "style-badge";
        badge.textContent = styleLabel;
        caption.appendChild(badge);
    }

    const downloadLink = document.createElement("a");
    downloadLink.href = imageDataUrl;
    downloadLink.download = "generated-image.png";
    downloadLink.textContent = "Download";
    downloadLink.className = "download-link";

    figure.appendChild(img);
    figure.appendChild(caption);
    figure.appendChild(downloadLink);
    resultEl.prepend(figure);
}
