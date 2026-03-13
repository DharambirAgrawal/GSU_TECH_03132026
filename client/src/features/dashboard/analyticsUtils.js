const compactFormatter = new Intl.NumberFormat("en-US", {
  notation: "compact",
  maximumFractionDigits: 1,
});

const integerFormatter = new Intl.NumberFormat("en-US", {
  maximumFractionDigits: 0,
});

export function safeArray(value) {
  return Array.isArray(value) ? value : [];
}

export function formatCompactNumber(value) {
  const numericValue = Number(value || 0);
  return compactFormatter.format(numericValue);
}

export function formatInteger(value) {
  const numericValue = Number(value || 0);
  return integerFormatter.format(numericValue);
}

export function toNumber(value, fallback = 0) {
  const numericValue = Number(value);
  return Number.isFinite(numericValue) ? numericValue : fallback;
}

export function clampNumber(value, min = 0, max = 100) {
  return Math.min(max, Math.max(min, toNumber(value, min)));
}

export function formatPercent(value, fractionDigits = 0) {
  const numericValue = Number(value || 0);
  return `${numericValue.toFixed(fractionDigits).replace(/\.0+$/, "")}%`;
}

export function formatScore(value, fractionDigits = 0) {
  return formatPercent(clampNumber(value), fractionDigits);
}

export function formatDateTime(value) {
  if (!value) {
    return "Not available yet";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "Not available yet";
  }

  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
}

export function formatDate(value) {
  if (!value) {
    return "Not available yet";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "Not available yet";
  }

  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
  }).format(date);
}

export function truncateText(value, maxLength = 140) {
  const text = String(value || "").trim();
  if (text.length <= maxLength) {
    return text;
  }

  return `${text.slice(0, maxLength).trimEnd()}…`;
}

export function startCase(value) {
  return String(value || "")
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

export function formatRelativeTime(value) {
  if (!value) {
    return "No recent update";
  }

  const timestamp = new Date(value);
  if (Number.isNaN(timestamp.getTime())) {
    return "No recent update";
  }

  const diffInMs = timestamp.getTime() - Date.now();
  const diffInHours = Math.round(diffInMs / (1000 * 60 * 60));
  const formatter = new Intl.RelativeTimeFormat("en-US", { numeric: "auto" });

  if (Math.abs(diffInHours) < 24) {
    return formatter.format(diffInHours, "hour");
  }

  return formatter.format(Math.round(diffInHours / 24), "day");
}

export function getScoreTone(score) {
  const numericScore = Number(score || 0);
  if (numericScore >= 75) {
    return "positive";
  }
  if (numericScore >= 50) {
    return "warning";
  }
  return "danger";
}

export function getSeverityTone(severity) {
  switch (String(severity || "").toLowerCase()) {
    case "critical":
      return "danger";
    case "high":
      return "warning";
    case "medium":
      return "info";
    default:
      return "neutral";
  }
}

export function getPerformanceLabel(score) {
  const numericScore = clampNumber(score);
  if (numericScore >= 80) {
    return "Strong";
  }
  if (numericScore >= 60) {
    return "Watch";
  }
  return "Needs attention";
}

export function buildSeveritySummary(errorBreakdown) {
  return safeArray(errorBreakdown).reduce((summary, item) => {
    const severity = String(item?.severity || "unknown").toLowerCase();
    const count = Number(item?.count || 0);
    summary[severity] = (summary[severity] || 0) + count;
    return summary;
  }, {});
}

export function getMentionRate(analytics) {
  const citations = Number(analytics?.summary?.total_citations || 0);
  const runs = Number(analytics?.summary?.total_model_runs || 0);
  if (!runs) {
    return 0;
  }
  return (citations / runs) * 100;
}

export function getTopItem(items, metric = "mentions") {
  return safeArray(items).reduce((top, item) => {
    if (!top) {
      return item;
    }
    return toNumber(item?.[metric]) > toNumber(top?.[metric]) ? item : top;
  }, null);
}

export function getUniqueCount(items, selector) {
  const values = safeArray(items)
    .map((item) => selector(item))
    .filter(Boolean);
  return new Set(values).size;
}

export function getTrendDelta(trend) {
  const entries = safeArray(trend);
  if (entries.length < 2) {
    return 0;
  }

  const first = toNumber(entries[0]?.avg_fact_score);
  const last = toNumber(entries[entries.length - 1]?.avg_fact_score);
  return (last - first) * 100;
}

export function getTrendDirection(trend) {
  const delta = getTrendDelta(trend);
  if (delta > 2) {
    return "up";
  }
  if (delta < -2) {
    return "down";
  }
  return "flat";
}
