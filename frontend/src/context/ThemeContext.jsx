import { createContext, useContext, useEffect, useState } from "react";

const ThemeContext = createContext(null);

export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem("theme") || "dark";
  });
  const [language, setLanguage] = useState(() => {
    return localStorage.getItem("language") || "es";
  });

  useEffect(() => {
    localStorage.setItem("theme", theme);
    localStorage.setItem("language", language);
    document.documentElement.classList.toggle("dark", theme === "dark");
  }, [theme, language]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === "light" ? "dark" : "light"));
  };

  const changeLanguage = (lang) => {
    setLanguage(lang);
  };

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme, language, changeLanguage }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) throw new Error("useTheme debe usarse dentro de ThemeProvider");
  return context;
}
