import { Route, Routes } from "react-router-dom";

import { AppShell } from "./components/AppShell";
import CountryIntelligence from "./pages/CountryIntelligence";
import CountryIntelligenceLanding from "./pages/CountryIntelligenceLanding";
import GlobalOverview from "./pages/GlobalOverview";
import { HowItWorks } from "./pages/HowItWorks";
import { PipelineTrigger } from "./pages/PipelineTrigger";
import { useEffect } from "react";
import { useLocation } from "react-router-dom";

export function App() {
  return (
    <div className="app">
      <ScrollToTop />
      <Routes>
        <Route element={<AppShell />}>
          <Route path="/" element={<GlobalOverview />} />
          <Route path="/country" element={<CountryIntelligenceLanding />} />
          <Route path="/country/:id" element={<CountryIntelligence />} />
          <Route path="/pipeline" element={<HowItWorks />} />
          <Route path="/trigger" element={<PipelineTrigger />} />
        </Route>
      </Routes>
    </div>
  );
}

function ScrollToTop() {
  const location = useLocation();
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [location.pathname]);
  return null;
}
