import { useState, useEffect } from 'react';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Productions from './pages/Productions';
import Calculator from './pages/Calculator';
import Jurisdictions from './pages/Jurisdictions';
import AIAdvisor from './components/AIAdvisor';
import MMBConnector from './pages/MMBConnector';
import ScheduleParser from './pages/ScheduleParser';
import PendingRules from './pages/PendingRules';
import LocalRules from './pages/LocalRules';
import ScenarioCalculator from './pages/ScenarioCalculator';
import Maximizer from './pages/Maximizer';
import Admin from './pages/Admin';
import Settings from './pages/Settings';
import Login from './pages/Login';
import { useAuthStore } from './store/auth';
import { FeatureFlagPanel } from './components/DevTools/FeatureFlagPanel';

function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const { isAuthenticated, loadFromStorage } = useAuthStore();

  useEffect(() => {
    loadFromStorage();
  }, [loadFromStorage]);

  const tabComponents: Record<string, React.ReactNode> = {
    dashboard:    <Dashboard />,
    productions:  <Productions />,
    calculator:   <Calculator />,
    jurisdictions: <Jurisdictions />,
    advisor:      <AIAdvisor />,
    mmb:          <MMBConnector />,
    schedule:     <ScheduleParser />,
    pendingRules:    <PendingRules />,
    localRules:      <LocalRules />,
    scenarioCalc:    <ScenarioCalculator />,
    maximizer:       <Maximizer />,
    admin:        <Admin />,
    settings:     <Settings />,
  };

  if (!isAuthenticated) {
    return <Login />;
  }

  return (
    <>
      <Layout activeTab={activeTab} onTabChange={setActiveTab}>
        {tabComponents[activeTab] || tabComponents.dashboard}
      </Layout>
      <FeatureFlagPanel />
    </>
  );
}

export default App;
