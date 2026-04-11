import { Route, Routes } from "react-router-dom";

import { AppShell } from "./components/AppShell";
import CountryIntelligence from "./pages/CountryIntelligence";
import GlobalOverview from "./pages/GlobalOverview";
import { HowItWorks } from "./pages/HowItWorks";
import { PipelineTrigger } from "./pages/PipelineTrigger";

export function App() {
  return (
    <div className="app">
      <Routes>
        <Route element={<AppShell />}>
          <Route path="/" element={<GlobalOverview />} />
          <Route path="/country/:id" element={<CountryIntelligence />} />
          <Route path="/pipeline" element={<HowItWorks />} />
          <Route path="/trigger" element={<PipelineTrigger />} />
        </Route>
      </Routes>
    </div>
  );
}
