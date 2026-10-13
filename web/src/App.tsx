import { HashRouter, Navigate, Route, Routes } from "react-router-dom";
import { Layout, type NavItem } from "./components/Layout";
import { ConsoleScreen } from "./screens/Console";
import { EvidenceScreen } from "./screens/Evidence";
import { HandoverScreen } from "./screens/Handover";
import { InspectionScreen } from "./screens/Inspection";
import { LabScreen } from "./screens/Lab";
import { MethodScreen } from "./screens/Method";
import { PlantScreen } from "./screens/Plant";
import { PoliciesScreen } from "./screens/Policies";
import { ReplayScreen } from "./screens/Replay";
import { TimelineScreen } from "./screens/Timeline";

export const NAV: NavItem[] = [
  { path: "/", key: "console" },
  { path: "/timeline", key: "timeline" },
  { path: "/evidence", key: "evidence" },
  { path: "/lab", key: "lab" },
  { path: "/policies", key: "policies" },
  { path: "/inspection", key: "inspection" },
  { path: "/plant", key: "plant" },
  { path: "/replay", key: "replay" },
  { path: "/method", key: "method" },
  { path: "/handover", key: "handover" },
];

export function AppRoutes() {
  return (
    <Layout nav={NAV}>
      <Routes>
        <Route path="/" element={<ConsoleScreen />} />
        <Route path="/timeline" element={<TimelineScreen />} />
        <Route path="/evidence" element={<EvidenceScreen />} />
        <Route path="/lab" element={<LabScreen />} />
        <Route path="/policies" element={<PoliciesScreen />} />
        <Route path="/inspection" element={<InspectionScreen />} />
        <Route path="/plant" element={<PlantScreen />} />
        <Route path="/replay" element={<ReplayScreen />} />
        <Route path="/method" element={<MethodScreen />} />
        <Route path="/handover" element={<HandoverScreen />} />
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
