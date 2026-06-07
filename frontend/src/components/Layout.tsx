import { LayoutDashboard, Clapperboard, Calculator, Globe, Bot, Bell, LogOut, FlaskConical, Settings, Link2, ClipboardCheck, BookOpen, Layers, Zap, CalendarClock, CalendarRange, GitMerge } from 'lucide-react';
import { useAuthStore } from '../store/auth';


interface LayoutProps {
  children: React.ReactNode;
  activeTab: string;
  onTabChange: (tab: string) => void;
}

const tabs = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'productions', label: 'Productions', icon: Clapperboard },
  { id: 'calculator', label: 'Incentive Calculator', icon: Calculator },
  { id: 'jurisdictions', label: 'Jurisdictions', icon: Globe },
  { id: 'advisor', label: 'AI Advisor', icon: Bot, badge: 'NEW' },
  { id: 'mmb', label: 'MMB Connector', icon: Link2, badge: 'NEW' },
  { id: 'productionSchedule', label: 'Production Schedule', icon: CalendarRange, badge: 'NEW' },
  { id: 'schedule', label: 'Transmission Log', icon: CalendarClock, badge: 'NEW' },
  { id: 'localRules',   label: 'Local Rules',       icon: BookOpen },
  { id: 'pendingRules', label: 'Rule Review',       icon: ClipboardCheck },
  { id: 'scenarioCalc', label: 'Scenario Calculator', icon: Layers },
  { id: 'maximizer',   label: 'Maximizer',            icon: Zap, badge: 'NEW' },
  { id: 'conflicts',   label: 'Conflicts',            icon: GitMerge, badge: 'NEW' },
  { id: 'settings', label: 'Notifications', icon: Bell },
];

const adminTab = { id: 'admin', label: 'Admin', icon: Settings };

function Layout({ children, activeTab, onTabChange }: LayoutProps) {
  const { user, logout } = useAuthStore();
  const usingMockData = false;

  const initials = user?.email
    ? user.email.slice(0, 2).toUpperCase()
    : 'PF';

  return (
    <div className="flex h-screen bg-slate-50 font-sans">
      {/* Sidebar */}
      <aside className="w-64 bg-[#13151a] text-slate-300 flex flex-col fixed h-full z-20 shrink-0">
        {/* Logo */}
        <div className="px-5 py-6 flex items-center gap-3">
          <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center text-white font-bold text-sm">
            $
          </div>
          <span className="text-white text-[17px] font-bold tracking-wide">SceneIQ</span>
        </div>

        {/* Mock data indicator — only visible when USE_REAL_API=false */}
        {usingMockData && (
          <div className="mx-3 mb-3 flex items-center gap-2 px-3 py-2 bg-amber-500/10 border border-amber-500/30 rounded-lg">
            <FlaskConical className="w-3.5 h-3.5 text-amber-400 shrink-0" />
            <span className="text-amber-400 text-[11px] font-semibold uppercase tracking-wide">Mock Data</span>
          </div>
        )}

        {/* Nav */}
        <nav className="flex-1 px-3 space-y-0.5">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => onTabChange(tab.id)}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-[#2563eb] text-white'
                    : 'text-slate-400 hover:text-white hover:bg-white/5'
                }`}
              >
                <Icon className="w-[18px] h-[18px] shrink-0" />
                <span className="flex-1 text-left">{tab.label}</span>
                {tab.badge && (
                  <span className="px-1.5 py-0.5 bg-blue-500 text-white text-[10px] uppercase font-bold rounded-sm leading-none">
                    {tab.badge}
                  </span>
                )}
              </button>
            );
          })}
          {user?.role === 'admin' && (
            <button
              onClick={() => onTabChange(adminTab.id)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                activeTab === adminTab.id
                  ? 'bg-[#2563eb] text-white'
                  : 'text-slate-400 hover:text-white hover:bg-white/5'
              }`}
            >
              <Settings className="w-[18px] h-[18px] shrink-0" />
              <span className="flex-1 text-left">{adminTab.label}</span>
            </button>
          )}
        </nav>

        {/* User section */}
        <div className="mt-auto px-4 py-4 border-t border-white/8">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-slate-600 rounded-full flex items-center justify-center text-[11px] text-white font-semibold shrink-0">
              {initials}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-white text-sm font-medium truncate">{user?.email ?? 'Unknown'}</p>
              <p className="text-slate-500 text-xs truncate capitalize">{user?.role ?? 'admin'}</p>
            </div>
            <button
              onClick={logout}
              title="Sign out"
              aria-label="Sign out"
              className="text-slate-500 hover:text-red-400 transition-colors shrink-0"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex-1 ml-64 flex flex-col min-h-screen">
        <main className="flex-1 bg-slate-50 p-8 overflow-y-auto">
          {children}
        </main>
        <footer className="bg-slate-50 border-t border-slate-200 px-8 py-3">
          <p className="text-xs text-slate-400">SceneIQ &copy; 2026 — Scene Reader Studio Technologies LLC</p>
        </footer>
      </div>
    </div>
  );
}

export default Layout;
