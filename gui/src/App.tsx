import { Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Inventory from './pages/Inventory';
import Analytics from './pages/Analytics';
import PricingForecast from './pages/PricingForecast';
import Import from './pages/Import';
import CommerceIntelligencePlatform from './pages/CommerceIntelligencePlatform';

function App() {
  return (
    <div className="h-screen w-full overflow-hidden bg-gray-900 text-gray-200 font-sans">
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/inventory" element={<Inventory />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/pricing-forecast" element={<PricingForecast />} />
          <Route path="/commerce-intelligence" element={<CommerceIntelligencePlatform />} />
          <Route path="/import" element={<Import />} />
        </Routes>
      </Layout>
    </div>
  );
}

export default App;