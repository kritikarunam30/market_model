const LoadingSpinner = ({ message = 'Loading...' }) => {
  return (
    <div className="flex flex-col items-center justify-center py-12">
      <div className="spinner"></div>
      <p className="text-neon-green mt-4 text-sm">{message}</p>
    </div>
  );
};

export default LoadingSpinner;
