const Loader = () => {
    return (
        <div className="flex space-x-2">
            <div className="w-3 h-3 bg-gray-500 dark:bg-white rounded-full animate-bounce"></div>
            <div className="w-3 h-3 bg-gray-500 dark:bg-white rounded-full animate-bounce delay-150"></div>
            <div className="w-3 h-3 bg-gray-500 dark:bg-white rounded-full animate-bounce delay-300"></div>
        </div>
    );
};

export default Loader;
