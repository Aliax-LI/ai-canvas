import { Outlet, useLocation } from "react-router-dom";
import { motion } from "framer-motion";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";

export function ProductShell() {
  const location = useLocation();

  return (
    <div data-testid="product-shell" className="flex h-full min-h-0 bg-background">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar />
        <motion.main
          key={location.pathname}
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.15, ease: "easeOut" }}
          className="flex-1 overflow-auto p-page"
        >
          <Outlet />
        </motion.main>
      </div>
    </div>
  );
}
