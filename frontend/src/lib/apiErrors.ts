import axios from "axios";

export function parseApiError(err: unknown, fallback: string): string {
  if (axios.isAxiosError(err)) {
    const detail = err.response?.data?.detail;
    if (typeof detail === "string" && detail.trim()) {
      return detail;
    }
    if (Array.isArray(detail)) {
      return detail.map((item) => String(item)).join("\n");
    }
    if (err.code === "ECONNABORTED") {
      return (
        "Investigation timed out. The cluster may be slow to reach.\n\n" +
        "Please wait and try again, or verify cluster connectivity."
      );
    }
    if (!err.response) {
      return (
        "Unable to reach the backend API.\n\n" +
        "Please verify the backend is running at NEXT_PUBLIC_API_BASE_URL."
      );
    }
    if (err.response.status === 401 || err.response.status === 403) {
      return "Authentication issue. Please sign in again and retry.";
    }
  }

  if (err instanceof Error && err.message) {
    return err.message;
  }

  return fallback;
}
