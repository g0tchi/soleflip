import { Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import ModernDashboard from './pages/ModernDashboard';
import Inventory from './pages/Inventory';
import ModernInventory from './pages/ModernInventory';
import Analytics from './pages/Analytics';
import ModernAnalytics from './pages/ModernAnalytics';
import PricingForecast from './pages/PricingForecast';
import Import from './pages/Import';
import Database from './pages/Database';
import ModernDataManagement from './pages/ModernDataManagement';
import ModernSettings from './pages/ModernSettings';
import { useTheme } from './contexts/ThemeContext';

function App() {
  const { theme } = useTheme();
  
  const isModernTheme = theme === 'happy-hues-modern';
  
  return (
    <div className={`h-screen w-full overflow-hidden ${
      isModernTheme 
        ? 'bg-gray-900 text-gray-200 font-sans' 
        : 'bg-dark-bg text-retro-cyan font-mono'
    }`}>
      <Layout>
        <Routes>
          <Route path="/" element={isModernTheme ? <ModernDashboard /> : <Dashboard />} />
          <Route path="/inventory" element={isModernTheme ? <ModernInventory /> : <Inventory />} />
          <Route path="/analytics" element={isModernTheme ? <ModernAnalytics /> : <Analytics />} />
          <Route path="/pricing-forecast" element={<PricingForecast />} />
          <Route path="/data-management" element={isModernTheme ? <ModernDataManagement /> : <Database />} />
          <Route path="/import" element={<Import />} />
          <Route path="/database" element={<Database />} />
          <Route path="/settings" element={<ModernSettings />} />
        </Routes>
      </Layout>
    </div>
  );
}

export default App;