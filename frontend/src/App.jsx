import { Routes, Route } from 'react-router-dom';
import { GlobalOverview } from './pages/GlobalOverview';
import { CountryIntelligence } from './pages/CountryIntelligence';
import { HowItWorks } from './pages/HowItWorks';
import { PipelineTrigger } from './pages/PipelineTrigger';

export function App() {
  return (
    <div className="app">
      <Routes>
        <Route path="/" element={<GlobalOverview />} />
        <Route path="/country/:id" element={<CountryIntelligence />} />
        <Route path="/pipeline" element={<HowItWorks />} />
        <Route path="/trigger" element={<PipelineTrigger />} />
      </Routes>
    </div>
  );
}
