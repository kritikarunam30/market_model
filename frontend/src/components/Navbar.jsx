import { Link, useLocation } from 'react-router-dom';
import { FaChartLine, FaHome, FaNetworkWired } from 'react-icons/fa';

const NAV_ITEMS = [
  { path: '/', icon: FaHome, label: 'Home' },
  { path: '/dashboard', icon: FaChartLine, label: 'Dashboard' },
];

const BASE_LINK_CLASS = 'flex items-center space-x-2 px-4 py-2 rounded-lg transition-all';
const ACTIVE_LINK_CLASS = 'bg-neon-green/20 text-neon-green border border-neon-green/30';
const INACTIVE_LINK_CLASS = 'text-gray-300 hover:text-neon-green hover:bg-neon-green/10';

const Navbar = () => {
  const location = useLocation();

  const isActive = (path) => location.pathname === path;

  return (
    <nav className="glass sticky top-0 z-50 border-b border-neon-green/20">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <div className="flex items-center space-x-3">
            <FaNetworkWired className="text-neon-green text-2xl" />
            <span className="text-xl font-bold text-neon-green">
              Market Contagion
            </span>
          </div>

          {/* Navigation Links */}
          <div className="flex space-x-4">
            {NAV_ITEMS.map((item) => {
              const Icon = item.icon;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`${BASE_LINK_CLASS} ${isActive(item.path) ? ACTIVE_LINK_CLASS : INACTIVE_LINK_CLASS}`}
                >
                  <Icon />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
