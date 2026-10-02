const styles = {
  editorial: {
    name: "Editorial",
    description: "A spacious product-planning system for proposals, strategy, and decision records."
  },
  newsroom: {
    name: "Newsroom",
    description: "A compact cream-paper system for reports, essays, research, and publication-like reading."
  },
  "humanist-blog": {
    name: "Humanist blog",
    description: "A warm, calm long-form system for playbooks, technical explainers, and operating guides."
  },
  notebook: {
    name: "Notebook",
    description: "A ruled-paper handwriting system for teaching notes, walkthroughs, and reflective documents."
  }
};

const styleOrder = Object.keys(styles);
const frame = document.querySelector("#preview-frame");
const fullExample = document.querySelector("#full-example");
const browserLabel = document.querySelector("#browser-label");
const styleName = document.querySelector("#style-name");
const styleDescription = document.querySelector("#style-description");
const gallery = document.querySelector(".gallery");
const tourToggle = document.querySelector("#tour-toggle");
let activeStyle = "editorial";
let tourPaused = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
let tourTimer;

function selectStyle(style, userInitiated = false) {
  if (!styles[style]) return;
  activeStyle = style;
  const url = `previews/${style}-preview.html`;
  frame.src = url;
  fullExample.href = url;
  browserLabel.textContent = `${style}-preview.html`;
  styleName.textContent = styles[style].name;
  styleDescription.textContent = styles[style].description;
  document.querySelectorAll("[data-style]").forEach((button) => {
    button.setAttribute("aria-selected", button.dataset.style === style ? "true" : "false");
  });
  if (userInitiated) restartTour();
}

function scheduleTour() {
  clearInterval(tourTimer);
  if (tourPaused) return;
  tourTimer = window.setInterval(() => {
    const next = styleOrder[(styleOrder.indexOf(activeStyle) + 1) % styleOrder.length];
    selectStyle(next);
  }, 4000);
}

function restartTour() {
  const progress = document.querySelector("#tour-progress i");
  progress.style.animation = "none";
  requestAnimationFrame(() => {
    progress.style.animation = "";
    scheduleTour();
  });
}

document.querySelectorAll("[data-style]").forEach((button) => {
  button.addEventListener("click", () => selectStyle(button.dataset.style, true));
});

document.querySelectorAll("[data-viewport]").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelector(".preview-stage").dataset.viewport = button.dataset.viewport;
    document.querySelectorAll("[data-viewport]").forEach((item) => item.classList.toggle("is-active", item === button));
  });
});

tourToggle.addEventListener("click", () => {
  tourPaused = !tourPaused;
  tourToggle.setAttribute("aria-pressed", tourPaused ? "true" : "false");
  tourToggle.textContent = tourPaused ? "Play 16-second tour" : "Pause 16-second tour";
  gallery.classList.toggle("is-paused", tourPaused);
  scheduleTour();
});

document.querySelectorAll("[data-copy]").forEach((button) => {
  button.addEventListener("click", async () => {
    const source = document.querySelector(button.dataset.copy);
    try {
      await navigator.clipboard.writeText(source.textContent.trim());
      const original = button.textContent;
      button.textContent = "Copied";
      window.setTimeout(() => { button.textContent = original; }, 1400);
    } catch (_) {
      const range = document.createRange();
      range.selectNodeContents(source);
      window.getSelection().removeAllRanges();
      window.getSelection().addRange(range);
    }
  });
});

scheduleTour();
