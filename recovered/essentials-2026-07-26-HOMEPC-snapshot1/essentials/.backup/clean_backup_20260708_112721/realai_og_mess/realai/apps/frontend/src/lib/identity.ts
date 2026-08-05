const USER_KEY = "realai:userId";

export function getOrCreateUserId(): string {
  if (typeof window === "undefined") return "anonymous";
  try {
    let id = localStorage.getItem(USER_KEY);
    if (!id) {
      id =
        typeof crypto !== "undefined" && "randomUUID" in crypto
          ? crypto.randomUUID()
          : `u_${Date.now().toString(36)}`;
      localStorage.setItem(USER_KEY, id);
    }
    return id;
  } catch {
    return "anonymous";
  }
}