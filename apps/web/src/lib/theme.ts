const THEME_KEY = "studio_theme";
const LEGACY_THEME_KEY = "canvas_theme";

export type Theme = "light" | "dark";

export function getStoredTheme(): Theme {
  try {
    const value =
      localStorage.getItem(THEME_KEY) ?? localStorage.getItem(LEGACY_THEME_KEY);
    return value === "dark" ? "dark" : "light";
  } catch {
    return "light";
  }
}

export function setStoredTheme(theme: Theme): void {
  try {
    localStorage.setItem(THEME_KEY, theme);
    localStorage.setItem(LEGACY_THEME_KEY, theme);
  } catch {
    // ignore quota / private mode
  }
}

export function applyTheme(theme: Theme): void {
  document.documentElement.classList.toggle("dark", theme === "dark");
}

export function toggleTheme(): Theme {
  const next: Theme = getStoredTheme() === "dark" ? "light" : "dark";
  setStoredTheme(next);
  applyTheme(next);
  return next;
}
