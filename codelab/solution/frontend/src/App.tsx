import { Routes, Route, Navigate } from "react-router-dom";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import RunView from "./pages/RunView";
import Sources from "./pages/Sources";
import Voice from "./pages/Voice";
import Skills from "./pages/Skills";
import Agents from "./pages/Agents";
import History from "./pages/History";

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/runs/:id" element={<RunView />} />
        <Route path="/sources" element={<Sources />} />
        <Route path="/voice" element={<Voice />} />
        <Route path="/skills" element={<Skills />} />
        <Route path="/agents" element={<Agents />} />
        <Route path="/history" element={<History />} />
      </Routes>
    </Layout>
  );
}
