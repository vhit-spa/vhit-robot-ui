import "./styles.css";

import {
  ActuatorViewer,
} from "./viewer/ActuatorViewer.js";

const JOG_REPEAT_INTERVAL_MS = 100;
const STATE_REFRESH_INTERVAL_MS = 500;

const pageUrl = new URL(window.location.href);
const bearerToken = pageUrl.searchParams.get("token");

if (bearerToken !== null) {
  pageUrl.searchParams.delete("token");
  window.history.replaceState(null, "", pageUrl);
}


function apiFetch(path, options = {}) {
  const headers = new Headers(options.headers);

  if (bearerToken !== null) {
    headers.set("Authorization", `Bearer ${bearerToken}`);
  }

  return fetch(path, {
    ...options,
    headers,
  });
}

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


const teachWaypointButton = document.getElementById(
  "teach-waypoint",
);

const waypointNameInput = document.getElementById(
  "waypoint-name",
);

const waypointListElement = document.getElementById(
  "waypoint-list",
);

const playWaypointsButton = document.getElementById(
  "play-waypoints",
);

const playbackDurationInput = document.getElementById(
  "playback-duration",
);

const playbackHoldTimeInput = document.getElementById(
  "playback-hold-time",
);

const waypointResultElement = document.getElementById(
  "waypoint-result",
);


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
    const response = await apiFetch("./api/v1/state", {
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
    const response = await apiFetch("./api/v1/jog", {
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

async function loadWaypoints() {
  try {
    const response = await apiFetch(
      "./api/v1/waypoints",
      {
        cache: "no-store",
      },
    );

    const result = await response.json();

    if (!response.ok) {
      throw new Error(
        result.error ?? "Unable to load waypoints",
      );
    }

    renderWaypoints(result.waypoints);
  } catch (error) {
    waypointResultElement.textContent = error.message;
  }
}


function renderWaypoints(waypoints) {
  waypointListElement.replaceChildren();

  if (waypoints.length === 0) {
    const emptyMessage = document.createElement("p");
    emptyMessage.textContent = "No waypoints stored.";
    waypointListElement.appendChild(emptyMessage);
    return;
  }

  waypoints.forEach((waypoint, index) => {
    const row = document.createElement("div");
    row.className = "waypoint-row";

    const description = document.createElement("div");

    const name = document.createElement("strong");
    name.textContent = waypoint.name;

    const position = document.createElement("span");
    position.textContent =
      `${waypoint.position.toFixed(4)} rad`;

    description.append(name, position);

    const controls = document.createElement("div");
    controls.className = "waypoint-actions";

    const executeButton = document.createElement("button");
    executeButton.type = "button";
    executeButton.textContent = "Move";

    executeButton.addEventListener("click", () => {
      executeWaypoint(waypoint.id);
    });

    const deleteButton = document.createElement("button");
    deleteButton.type = "button";
    deleteButton.textContent = "Delete";

    deleteButton.addEventListener("click", () => {
      deleteWaypoint(waypoint.id);
    });

    controls.append(
      executeButton,
      deleteButton,
    );

    const indexElement = document.createElement("span");
    indexElement.textContent = `${index + 1}.`;
    indexElement.className = "waypoint-index";

    row.append(
      indexElement,
      description,
      controls,
    );

    waypointListElement.appendChild(row);
  });
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

async function teachWaypoint() {
  waypointResultElement.textContent = "";

  try {
    const response = await apiFetch(
      "./api/v1/waypoints",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          name: waypointNameInput.value,
        }),
      },
    );

    const result = await response.json();

    if (!response.ok) {
      throw new Error(
        result.error ?? "Waypoint creation failed",
      );
    }

    waypointNameInput.value = "";

    waypointResultElement.textContent =
      `Stored ${result.name}`;

    await loadWaypoints();
  } catch (error) {
    waypointResultElement.textContent = error.message;
  }
}

async function executeWaypoint(waypointId) {
  waypointResultElement.textContent = "";

  try {
    const duration = Number(
      playbackDurationInput.value
    );

    const response = await apiFetch(
      `./api/v1/waypoints/${waypointId}/execute`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          duration,
        }),
      },
    );

    const result = await response.json();

    if (!response.ok) {
      throw new Error(
        result.error ?? "Waypoint execution failed",
      );
    }

    waypointResultElement.textContent =
      `Moving to ${result.waypoint.name}`;
  } catch (error) {
    waypointResultElement.textContent = error.message;
  }
}

async function deleteWaypoint(waypointId) {
  try {
    const response = await apiFetch(
      `./api/v1/waypoints/${waypointId}`,
      {
        method: "DELETE",
      },
    );

    const result = await response.json();

    if (!response.ok) {
      throw new Error(
        result.error ?? "Waypoint deletion failed",
      );
    }

    await loadWaypoints();
  } catch (error) {
    waypointResultElement.textContent = error.message;
  }
}

async function playWaypoints() {
  waypointResultElement.textContent = "";

  try {
    const moveDuration = Number(
      playbackDurationInput.value
    );

    const holdTime = Number(
      playbackHoldTimeInput.value
    );

    const response = await apiFetch(
      "./api/v1/playback",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          move_duration: moveDuration,
          hold_time: holdTime,
        }),
      },
    );

    const result = await response.json();

    if (!response.ok) {
      throw new Error(
        result.error ?? "Playback failed",
      );
    }

    waypointResultElement.textContent =
      `Playing ${result.waypoint_count} waypoints`;
  } catch (error) {
    waypointResultElement.textContent = error.message;
  }
}

teachWaypointButton.addEventListener(
  "click",
  teachWaypoint,
);

playWaypointsButton.addEventListener(
  "click",
  playWaypoints,
);

loadWaypoints();

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

window.setInterval(updateState, STATE_REFRESH_INTERVAL_MS);
