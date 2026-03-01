export function normalizeCode(value) {
  return String(value || "")
    .trim()
    .toUpperCase();
}

export function normalizeIsoCode(rawCode) {
  if (!rawCode) return "";
  const code = String(rawCode).trim().toUpperCase();
  if (!code || code === "-99" || code === "--") return "";

  if (code.includes("-")) {
    const parts = code.split("-");
    const suffix = parts[parts.length - 1];
    if (suffix && (suffix.length === 2 || suffix.length === 3)) {
      return suffix;
    }
  }

  return code;
}

export function getCountryCodeA2FromProps(props, codeMap = {}) {
  const codeCandidates = [
    props?.iso_a2,
    props?.iso_a2_eh,
    props?.wb_a2,
    props?.iso_a3,
    props?.adm0_a3,
    props?.sov_a3,
    props?.wb_a3,
  ];

  for (const rawCode of codeCandidates) {
    const normalizedCode = normalizeIsoCode(rawCode);
    if (!normalizedCode) continue;

    const a2Code =
      codeMap[normalizedCode] ||
      (normalizedCode.length === 2 ? normalizedCode : "");

    if (a2Code) return a2Code;
  }

  return "";
}

export function getCountryNameFromProps(props) {
  return (
    String(props?.name || props?.ADMIN || props?.admin || "").trim() ||
    "Unknown country"
  );
}

function wrapLongitude(lng) {
  if (!Number.isFinite(lng)) return 0;
  return ((lng + 180) % 360 + 360) % 360 - 180;
}

function unwrapRingLongitudes(ring) {
  const normalized = [];
  let previousLng = null;

  for (const point of ring || []) {
    if (!Array.isArray(point) || point.length < 2) continue;
    const rawLng = Number(point[0]);
    const lat = Number(point[1]);
    if (!Number.isFinite(rawLng) || !Number.isFinite(lat)) continue;

    if (previousLng === null) {
      previousLng = rawLng;
    } else {
      let candidate = rawLng;
      while (candidate - previousLng > 180) candidate -= 360;
      while (candidate - previousLng < -180) candidate += 360;
      previousLng = candidate;
    }

    normalized.push([previousLng, lat]);
  }

  return normalized;
}

function getRingArea(ring) {
  if (!Array.isArray(ring) || ring.length < 3) return 0;

  let area = 0;
  for (let index = 0; index < ring.length; index += 1) {
    const current = ring[index];
    const next = ring[(index + 1) % ring.length];
    area += current[0] * next[1] - next[0] * current[1];
  }

  return area / 2;
}

export function getLargestOuterRing(geometry) {
  if (!geometry?.type || !Array.isArray(geometry.coordinates)) {
    return null;
  }

  const candidates = [];
  if (geometry.type === "Polygon") {
    if (Array.isArray(geometry.coordinates[0])) {
      candidates.push(geometry.coordinates[0]);
    }
  } else if (geometry.type === "MultiPolygon") {
    for (const polygon of geometry.coordinates) {
      if (Array.isArray(polygon) && Array.isArray(polygon[0])) {
        candidates.push(polygon[0]);
      }
    }
  }

  let bestRing = null;
  let bestArea = -1;
  for (const ring of candidates) {
    const unwrappedRing = unwrapRingLongitudes(ring);
    const area = Math.abs(getRingArea(unwrappedRing));
    if (area > bestArea) {
      bestArea = area;
      bestRing = unwrappedRing;
    }
  }

  return bestRing;
}

export function getPolygonCentroid(ring) {
  if (!Array.isArray(ring) || ring.length < 3) return null;

  let signedAreaSum = 0;
  let centroidX = 0;
  let centroidY = 0;

  for (let index = 0; index < ring.length; index += 1) {
    const current = ring[index];
    const next = ring[(index + 1) % ring.length];
    const cross = current[0] * next[1] - next[0] * current[1];
    signedAreaSum += cross;
    centroidX += (current[0] + next[0]) * cross;
    centroidY += (current[1] + next[1]) * cross;
  }

  const area = signedAreaSum / 2;
  if (!Number.isFinite(area) || Math.abs(area) < 1e-8) return null;

  return [centroidY / (6 * area), wrapLongitude(centroidX / (6 * area))];
}
