"use strict";

const positionElement = document.getElementById("joint-position");
const statusElement = document.getElementById("connection-status");
const shaftElement = document.getElementById("actuator-shaft");
const resultElement = document.getElementById("command-result");

async function jog(direction) {
  resultElement.textContent = "";

  try {
    const response = await fetch("api/v1/jog", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ direction }),
    });

    const result = await response.json();

    if (!response.ok) {
      throw new Error(result.error ?? "Jog command rejected");
    }

    resultElement.textContent =
      direction > 0 ? "Positive jog sent" : "Negative jog sent";
  } catch (error) {
    resultElement.textContent = error.message;
  }
}

async function updateState() {
  try {
    const response = await fetch("api/v1/state", {
      cache: "no-store",
    });

    if (!response.ok) {
      throw new Error("State request failed");
    }

    const state = await response.json();

    if (
      state.feedback_fresh &&
      typeof state.position === "number"
    ) {
      positionElement.textContent = state.position.toFixed(4);

      statusElement.textContent = "Feedback connected";
      statusElement.className = "status connected";

      const degrees = state.position * 180 / Math.PI;
      shaftElement.style.transform = `rotate(${degrees}deg)`;
    } else {
      positionElement.textContent = "--";
      statusElement.textContent = "Feedback stale";
      statusElement.className = "status disconnected";
    }
  } catch {
    positionElement.textContent = "--";
    statusElement.textContent = "Gateway unavailable";
    statusElement.className = "status disconnected";
  }
}

document
  .getElementById("jog-negative")
  .addEventListener("click", () => jog(-1));

document
  .getElementById("jog-positive")
  .addEventListener("click", () => jog(1));

window.addEventListener("keydown", event => {
  if (event.repeat) {
    return;
  }

  if (event.key === "ArrowLeft") {
    event.preventDefault();
    jog(-1);
  }

  if (event.key === "ArrowRight") {
    event.preventDefault();
    jog(1);
  }
});

updateState();
window.setInterval(updateState, 200);