import { useNavigate } from 'react-router-dom';
import NeonButton from '../components/NeonButton';
import { FaChartLine, FaNetworkWired, FaBrain } from 'react-icons/fa';

const FEATURES = [
  {
    icon: <FaChartLine className="text-4xl" />,
    title: 'VAR Spillover',
    description: 'Analyze cross-market risk transmission using Vector Autoregression',
  },
  {
    icon: <FaNetworkWired className="text-4xl" />,
    title: 'Contagion Network',
    description: 'Visualize systemic risk propagation across global markets',
  },
  {
    icon: <FaBrain className="text-4xl" />,
    title: 'ML Forecasting',
    description: 'XGBoost-powered risk prediction with SHAP explanations',
  },
];

const HomePage = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen">
      {/* Hero Section */}
      <section className="relative overflow-hidden py-20 px-4">
        <div className="max-w-6xl mx-auto text-center">
          {/* Animated floating elements */}
          <div className="absolute top-20 left-10 w-32 h-32 bg-neon-green/10 rounded-full blur-3xl animate-float"></div>
          <div className="absolute bottom-20 right-10 w-40 h-40 bg-neon-blue/10 rounded-full blur-3xl animate-float" style={{ animationDelay: '2s' }}></div>

          <div className="relative z-10">
            <h1 className="text-6xl md:text-7xl font-bold mb-6 leading-tight">
              <br />
              <span className="text-neon-green">
                Global Market
              </span>
              <br />
              <span className="text-white">Contagion Intelligence</span>
            </h1>

            <p className="text-xl text-gray-300 mb-8 max-w-3xl mx-auto">
              Research-grade systemic risk modeling platform combining VAR analysis, 
              GARCH volatility, and ML forecasting for comprehensive 
              financial contagion assessment.
            </p>

            <div className="flex justify-center gap-4 mb-16">
              <NeonButton onClick={() => navigate('/dashboard')}>
                Run Contagion Analysis
              </NeonButton>
            </div>

            {/* Animated metrics */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6 max-w-4xl mx-auto">
              <div className="glass rounded-lg p-4 hover:shadow-neon transition-all">
                <div className="text-3xl font-bold text-neon-green">7</div>
                <div className="text-sm text-gray-400">Markets</div>
              </div>
              <div className="glass rounded-lg p-4 hover:shadow-neon transition-all">
                <div className="text-3xl font-bold text-neon-green">3</div>
                <div className="text-sm text-gray-400">Models</div>
              </div>
              <div className="glass rounded-lg p-4 hover:shadow-neon transition-all">
                <div className="text-3xl font-bold text-neon-green">800+</div>
                <div className="text-sm text-gray-400">Data Points</div>
              </div>
              <div className="glass rounded-lg p-4 hover:shadow-neon transition-all">
                <div className="text-3xl font-bold text-neon-green">Real-time</div>
                <div className="text-sm text-gray-400">Analysis</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20 px-4">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-4xl font-bold text-center mb-12">
            <span className="text-neon-green">
              Advanced Analytics
            </span>
          </h2>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 justify-center items-center text-center">
            {FEATURES.map((feature) => (
              <div
                key={feature.title}
                className="glass rounded-xl p-6 hover:shadow-neon transition-all hover:scale-105 cursor-pointer"
              >
                <div className="flex justify-center items-center text-neon-green mb-4">{feature.icon}</div>
                <h3 className="text-xl font-semibold mb-2 text-white">
                  {feature.title}
                </h3>
                <p className="text-gray-400 text-sm">{feature.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Tech Stack Section */}
      <section className="py-20 px-4 border-t border-neon-green/10">
        <div className="max-w-6xl mx-auto text-center">
          <h2 className="text-3xl font-bold mb-8 text-white">
            Powered by State-of-the-Art Technology
          </h2>
          <div className="flex flex-wrap justify-center gap-4">
            {['FastAPI', 'React', 'Plotly', 'XGBoost', 'Granger', 'VAR', 'NetworkX'].map((tech) => (
              <span
                key={tech}
                className="glass px-6 py-2 rounded-full text-neon-green border border-neon-green/30 hover:shadow-neon transition-all"
              >
                {tech}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 px-4">
        <div className="max-w-4xl mx-auto text-center glass rounded-2xl p-12 shadow-neon">
          <h2 className="text-4xl font-bold mb-4 text-white">
            Ready to Analyze Systemic Risk?
          </h2>
          <p className="text-gray-300 mb-8">
            Start exploring global market contagion patterns and risk transmission dynamics.
          </p>
          <NeonButton onClick={() => navigate('/dashboard')}>
            Launch Dashboard
          </NeonButton>
        </div>
      </section>
    </div>
  );
};

export default HomePage;
