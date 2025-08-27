import { Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Inventory from './pages/Inventory';
import Analytics from './pages/Analytics';
import Import from './pages/Import';
import Database from './pages/Database';
import Settings from './pages/Settings';

function App() {
  return (
    <div className="h-screen bg-dark-bg text-retro-cyan font-mono">
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/inventory" element={<Inventory />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/import" element={<Import />} />
          <Route path="/database" element={<Database />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </Layout>
    </div>
  );
}

export default App;