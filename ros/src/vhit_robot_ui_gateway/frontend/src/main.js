import "./styles.css";

import {
  ActuatorViewer,
} from "./viewer/ActuatorViewer.js";

const JOG_REPEAT_INTERVAL_MS = 100;

let jogIntervalId = null;
let activeJogDirection = 0;
let jogRequestInProgress = false;

const viewerContainer = document.getElementById(
  "actuator-viewer",
);

const positionElement = document.getElementById(
  "joint-position",
);

const viewerPositionElement = document.getElementById(
  "viewer-position",
);

const statusElement = document.getElementById(
  "connection-status",
);

const resultElement = document.getElementById(
  "command-result",
);

const jogNegativeButton = document.getElementById(
  "jog-negative",
);

const jogPositiveButton = document.getElementById(
  "jog-positive",
);

const resetCameraButton = document.getElementById(
  "reset-camera",
);


const viewer = new ActuatorViewer(viewerContainer);

viewerContainer
  .querySelector(".viewer-loading")
  ?.remove();

viewer.start();


function setControlsEnabled(enabled) {
  jogNegativeButton.disabled = !enabled;
  jogPositiveButton.disabled = !enabled;
}


function showUnavailableState(message) {
  statusElement.textContent = message;
  statusElement.className = "status disconnected";

  positionElement.textContent = "--";
  viewerPositionElement.textContent = "Position: -- rad";

  setControlsEnabled(false);
}


function applyRobotState(state) {
  const hasPosition = Number.isFinite(state.position);

  if (!hasPosition) {
    showUnavailableState(
      `Joint '${state.joint}' not received`,
    );

    return;
  }

  const positionText = state.position.toFixed(4);

  /*
   * Continue displaying the last valid position even when stale.
   * Motion controls remain disabled until feedback is fresh.
   */
  positionElement.textContent = positionText;

  viewerPositionElement.textContent =
    `Position: ${positionText} rad`;

  viewer.setPosition(state.position);

  if (!state.feedback_fresh) {
    const age = Number.isFinite(state.feedback_age_seconds)
      ? state.feedback_age_seconds.toFixed(2)
      : "unknown";

    statusElement.textContent =
      `Feedback stale (${age} s)`;

    statusElement.className = "status disconnected";

    setControlsEnabled(false);
    return;
  }

  statusElement.textContent = "Feedback connected";
  statusElement.className = "status connected";

  setControlsEnabled(true);
}


async function updateState() {
  try {
    const response = await fetch("./api/v1/state", {
      cache: "no-store",
    });

    if (!response.ok) {
      throw new Error(
        `State request failed with status ${response.status}`,
      );
    }

    const state = await response.json();

    applyRobotState(state);
  } catch (error) {
    console.error("Failed to update robot state:", error);

    showUnavailableState("Gateway unavailable");
  }
}


async function jog(direction) {
  if (direction !== -1 && direction !== 1) {
    throw new RangeError(
      "Jog direction must be -1 or 1",
    );
  }

  resultElement.textContent = "";

  try {
    const response = await fetch("./api/v1/jog", {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
      },

      body: JSON.stringify({
        direction,
      }),
    });

    const result = await response.json();

    if (!response.ok) {
      throw new Error(
        result.error ?? "Jog command rejected",
      );
    }

    resultElement.textContent =
      direction > 0
        ? "Positive jog sent"
        : "Negative jog sent";
  } catch (error) {
    console.error("Jog command failed:", error);
    resultElement.textContent = error.message;
  }
}

async function sendRepeatedJog(direction) {
  if (jogRequestInProgress) {
    return;
  }

  jogRequestInProgress = true;

  try {
    await jog(direction);
  } finally {
    jogRequestInProgress = false;
  }
}


function startJog(direction) {
  if (direction !== -1 && direction !== 1) {
    return;
  }

  if (activeJogDirection === direction) {
    return;
  }

  stopJog();

  activeJogDirection = direction;

  // Send one command immediately.
  sendRepeatedJog(direction);

  jogIntervalId = window.setInterval(() => {
    sendRepeatedJog(direction);
  }, JOG_REPEAT_INTERVAL_MS);
}


function stopJog() {
  activeJogDirection = 0;

  if (jogIntervalId !== null) {
    window.clearInterval(jogIntervalId);
    jogIntervalId = null;
  }
}


function configureHoldButton(button, direction) {
  button.addEventListener("pointerdown", event => {
    event.preventDefault();

    if (button.disabled) {
      return;
    }

    button.setPointerCapture(event.pointerId);
    startJog(direction);
  });

  button.addEventListener("pointerup", event => {
    if (button.hasPointerCapture(event.pointerId)) {
      button.releasePointerCapture(event.pointerId);
    }

    stopJog();
  });

  button.addEventListener("pointercancel", stopJog);
  button.addEventListener("lostpointercapture", stopJog);
}


configureHoldButton(jogNegativeButton, -1);
configureHoldButton(jogPositiveButton, 1);


window.addEventListener("blur", stopJog);

document.addEventListener("visibilitychange", () => {
  if (document.hidden) {
    stopJog();
  }
});

window.addEventListener("beforeunload", () => {
  stopJog();
  viewer.dispose();
});


resetCameraButton.addEventListener(
  "click",
  () => viewer.resetCamera(),
);


window.addEventListener("keydown", event => {
  if (event.key === "ArrowLeft") {
    event.preventDefault();

    if (!jogNegativeButton.disabled) {
      startJog(-1);
    }
  }

  if (event.key === "ArrowRight") {
    event.preventDefault();

    if (!jogPositiveButton.disabled) {
      startJog(1);
    }
  }
});


window.addEventListener("keyup", event => {
  if (
    event.key === "ArrowLeft" ||
    event.key === "ArrowRight"
  ) {
    event.preventDefault();
    stopJog();
  }
});


window.addEventListener("beforeunload", () => {
  viewer.dispose();
});


setControlsEnabled(false);
updateState();

window.setInterval(updateState, 100);