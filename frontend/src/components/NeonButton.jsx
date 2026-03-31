const VARIANTS = {
  primary: 'neon-btn text-black font-semibold',
  secondary: 'glass border-neon-green text-neon-green hover:bg-neon-green/10',
  danger: 'bg-red-600 hover:bg-red-700 text-white',
};

const NeonButton = ({ children, onClick, variant = 'primary', className = '' }) => {
  return (
    <button
      onClick={onClick}
      className={`px-6 py-3 rounded-lg transition-all duration-300 ${VARIANTS[variant]} ${className}`}
    >
      {children}
    </button>
  );
};

export default NeonButton;
