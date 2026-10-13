import { HashRouter, Navigate, Route, Routes } from "react-router-dom";
import { Layout, type NavItem } from "./components/Layout";
import { ConsoleScreen } from "./screens/Console";
import { EvidenceScreen } from "./screens/Evidence";

export const NAV: NavItem[] = [
  { path: "/", key: "console" },
  { path: "/evidence", key: "evidence" },
];

export function AppRoutes() {
  return (
    <Layout nav={NAV}>
      <Routes>
        <Route path="/" element={<ConsoleScreen />} />
        <Route path="/evidence" element={<EvidenceScreen />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  );
}

export function App() {
  return (
    <HashRouter>
      <AppRoutes />
    </HashRouter>
  );
}
