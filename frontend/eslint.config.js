import js from '@eslint/js'
import vue from 'eslint-plugin-vue'
import globals from 'globals'

const browserGlobals = {
  ...globals.browser,
  ...globals.es2025,
}

const nodeGlobals = {
  ...globals.node,
  ...globals.es2025,
}

export default [
  {
    ignores: [
      'coverage/**',
      'dist/**',
      'node_modules/**',
    ],
  },
  js.configs.recommended,
  ...vue.configs['flat/recommended'],
  {
    files: ['**/*.{js,vue}'],
    languageOptions: {
      ecmaVersion: 'latest',
      globals: browserGlobals,
      sourceType: 'module',
    },
    rules: {
      'no-unused-vars': ['error', {
        argsIgnorePattern: '^_',
        caughtErrorsIgnorePattern: '^_',
        varsIgnorePattern: '^_',
      }],
      'vue/attributes-order': 'off',
      'vue/html-self-closing': ['error', {
        html: {
          component: 'always',
          normal: 'always',
          void: 'always',
        },
        math: 'always',
        svg: 'always',
      }],
      'vue/max-attributes-per-line': 'off',
      'vue/multi-word-component-names': 'off',
      'vue/singleline-html-element-content-newline': 'off',
    },
  },
  {
    files: [
      'eslint.config.js',
      'vite.config.js',
    ],
    languageOptions: {
      globals: nodeGlobals,
    },
  },
  {
    files: [
      'src/**/*.test.js',
      'src/test/**/*.js',
    ],
    languageOptions: {
      globals: {
        ...browserGlobals,
        ...globals.vitest,
      },
    },
    rules: {
      'vue/one-component-per-file': 'off',
    },
  },
]
