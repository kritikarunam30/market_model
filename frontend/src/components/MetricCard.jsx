const MetricCard = ({ title, value, subtitle, trend, icon }) => {
  const trendColor = !trend ? 'text-gray-400' : trend > 0 ? 'text-red-400' : 'text-green-400';

  return (
    <div className="glass rounded-xl p-6 hover:shadow-neon transition-all">
      <div className="flex items-start justify-between mb-4">
        <div>
          <p className="text-gray-400 text-sm mb-1">{title}</p>
          <h3 className="text-3xl font-bold text-white">{value}</h3>
        </div>
        {icon && (
          <div className="text-neon-green text-2xl opacity-60">{icon}</div>
        )}
      </div>
      {subtitle && (
        <p className={`text-sm ${trendColor}`}>{subtitle}</p>
      )}
    </div>
  );
};

export default MetricCard;
