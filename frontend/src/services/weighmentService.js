const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api";
const USE_MOCKS = import.meta.env.VITE_USE_MOCKS !== "false";

const mockWeights = [0, 1842, 6528, 11896, 19444, 26418, 26421, 26420, 26422, 26420];
let weightIndex = 0;

const mockCameraFeeds = [
  { id: 1, title: "Camera 1", status: "Live", description: "Top platform overview" },
  { id: 2, title: "Camera 2", status: "Live", description: "Exit side vehicle view" },
];

async function safeFetch(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }

  return response.json();
}

export async function getLiveWeight() {
  if (USE_MOCKS) {
    weightIndex = (weightIndex + 1) % mockWeights.length;
    const current = mockWeights[weightIndex];
    const previous = mockWeights[(weightIndex - 1 + mockWeights.length) % mockWeights.length];

    return {
      weight: current,
      stable: Math.abs(current - previous) <= 2 && current > 0,
      source: "mock",
    };
  }

  try {
    const data = await safeFetch("/weighbridge-configs/automation_health/");
    const recent = data?.recent_automation_actions?.[0];
    const recentMatch = recent?.notes?.match(/([0-9]+(?:\.[0-9]+)?)/);
    return {
      weight: recentMatch ? Number(recentMatch[1]) : 0,
      stable: String(recent?.action || "").includes("STABLE"),
      source: "backend",
    };
  } catch {
    return {
      weight: 0,
      stable: false,
      source: "fallback",
    };
  }
}

export async function getCameraFeeds() {
  if (USE_MOCKS) {
    return mockCameraFeeds;
  }

  try {
    const data = await safeFetch("/cameras/");
    return (Array.isArray(data) ? data : data?.results || []).map((camera, index) => ({
      id: camera.id || index + 1,
      title: camera.camera_name || `Camera ${index + 1}`,
      status: camera.is_active ? "Live" : "Offline",
      description: camera.location || "Configured camera feed",
    }));
  } catch {
    return mockCameraFeeds;
  }
}

export async function getNextSerialNumber() {
  if (USE_MOCKS) {
    return 1;
  }

  try {
    const data = await safeFetch("/weight-records/");
    const records = Array.isArray(data) ? data : data?.results || [];
    return records.length + 1;
  } catch {
    return 1;
  }
}

export async function saveWeighment(payload) {
  if (USE_MOCKS) {
    return {
      status: "mock-saved",
      payload,
      timestamp: new Date().toISOString(),
    };
  }

  return safeFetch("/weight-records/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
