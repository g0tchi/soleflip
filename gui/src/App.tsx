import { Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Inventory from './pages/Inventory';
import QuickFlip from './pages/QuickFlip';
import Analytics from './pages/Analytics';
import PricingForecast from './pages/PricingForecast';
import Import from './pages/Import';
import CommerceIntelligencePlatform from './pages/CommerceIntelligencePlatform';

function App() {
  return (
    <div
      className="h-screen w-full overflow-hidden bg-gray-900 text-gray-200 font-sans"
      role="application"
      aria-label="SoleFlipper sneaker resale management application"
    >
      <Layout>
        <main role="main" aria-label="Main content area">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/inventory" element={<Inventory />} />
            <Route path="/quickflip" element={<QuickFlip />} />
            <Route path="/analytics" element={<Analytics />} />
            <Route path="/pricing-forecast" element={<PricingForecast />} />
            <Route path="/commerce-intelligence" element={<CommerceIntelligencePlatform />} />
            <Route path="/import" element={<Import />} />
          </Routes>
        </main>
      </Layout>
    </div>
  );
}

export default App;