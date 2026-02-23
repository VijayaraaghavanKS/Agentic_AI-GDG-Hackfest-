import { Link, Outlet, useLocation } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Moon, Sun, TrendingUp, BarChart3, LayoutDashboard, FlaskConical } from "lucide-react";
import { useState, useEffect } from "react";

export function Layout() {
  const [darkMode, setDarkMode] = useState(() => {
    if (typeof window !== "undefined") {
      return (
        localStorage.getItem("theme") === "dark" ||
        (!localStorage.getItem("theme") && window.matchMedia("(prefers-color-scheme: dark)").matches)
      );
    }
    return true;
  });
  const location = useLocation();

  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add("dark");
      localStorage.setItem("theme", "dark");
    } else {
      document.documentElement.classList.remove("dark");
      localStorage.setItem("theme", "light");
    }
  }, [darkMode]);

  return (
    <div className="h-screen flex flex-col bg-background">
      <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container max-w-screen-2xl flex h-14 items-center justify-between px-4">
          <div className="flex items-center gap-4">
            <Link to="/" className="flex items-center gap-2 hover:opacity-90">
              <TrendingUp className="h-6 w-6 text-primary" />
              <h1 className="text-xl font-bold">Trade Copilot</h1>
            </Link>
            <span className="px-2 py-0.5 text-xs font-medium bg-yellow-500/10 text-yellow-600 rounded-full border border-yellow-500/20">
              PAPER TRADING
            </span>
            <nav className="flex gap-1 ml-2">
              <Link to="/">
                <Button
                  variant={location.pathname === "/" ? "secondary" : "ghost"}
                  size="sm"
                  className="gap-1.5"
                >
                  <LayoutDashboard className="h-4 w-4" />
                  Dashboard
                </Button>
              </Link>
              <Link to="/market">
                <Button
                  variant={location.pathname === "/market" ? "secondary" : "ghost"}
                  size="sm"
                  className="gap-1.5"
                >
                  <BarChart3 className="h-4 w-4" />
                  Market
                </Button>
              </Link>
              <Link to="/analyze">
                <Button
                  variant={location.pathname === "/analyze" ? "secondary" : "ghost"}
                  size="sm"
                  className="gap-1.5"
                >
                  <FlaskConical className="h-4 w-4" />
                  Analyze
                </Button>
              </Link>
            </nav>
          </div>
          <Button variant="ghost" size="icon" onClick={() => setDarkMode(!darkMode)}>
            {darkMode ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
          </Button>
        </div>
      </header>
      <main className="w-full px-4 py-4 flex-1 overflow-y-auto">
        <Outlet />
      </main>
    </div>
  );
}
