module.exports = {
  testEnvironment: 'node',
  testMatch: [
    '**/tests/**/*.js'
  ],
  collectCoverageFrom: [
    'static/js/**/*.js',
    '!static/js/**/*.min.js'
  ],
  coverageDirectory: 'coverage',
  coverageReporters: ['text', 'lcov', 'html'],
  verbose: true,
  setupFilesAfterEnv: ['<rootDir>/tests/jest.setup.js']
};