import { NavLink } from "react-router-dom";

const NAV = [
  { to: "/dashboard", label: "Dashboard" },
  { to: "/sources", label: "Sources" },
  { to: "/voice", label: "Voice" },
  { to: "/skills", label: "Skills" },
  { to: "/agents", label: "Agents" },
  { to: "/history", label: "History" },
];

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen bg-gray-50">
      <aside className="w-48 bg-white border-r flex flex-col py-6 px-4 gap-1 shrink-0">
        <p className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-4">
          Daily Digest
        </p>
        {NAV.map((n) => (
          <NavLink
            key={n.to}
            to={n.to}
            className={({ isActive }) =>
              `px-3 py-2 rounded text-sm font-medium transition-colors ${
                isActive
                  ? "bg-indigo-50 text-indigo-700"
                  : "text-gray-600 hover:bg-gray-100"
              }`
            }
          >
            {n.label}
          </NavLink>
        ))}
      </aside>
      <main className="flex-1 overflow-auto p-8">{children}</main>
    </div>
  );
}
