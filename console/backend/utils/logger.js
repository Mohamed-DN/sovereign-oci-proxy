const logger = {
  info: (...args) => console.log('\x1b[34m[INFO]\x1b[0m', ...args),
  warn: (...args) => console.warn('\x1b[33m[WARN]\x1b[0m', ...args),
  error: (...args) => console.error('\x1b[31m[ERROR]\x1b[0m', ...args),
  debug: (...args) => {
    if (process.env.DEBUG || process.env.NODE_ENV === 'development') {
      console.log('\x1b[35m[DEBUG]\x1b[0m', ...args);
    }
  }
};

module.exports = logger;
