// ESLint flat config for the KerjaCerdas frontend.
//
// There was previously no linting here at all: CI ran
// `npm run lint --if-present || true` against a repo with no config, no
// dependency and no script, so `--if-present` exited 0 and the step named
// "ESLint" passed without checking anything.
//
// Scope is deliberately narrow for a first pass — correctness rules that catch
// real bugs (undefined variables, broken hooks, unreachable code), not style.
// Formatting is not enforced; adding a 40-component codebase to a strict style
// preset in one go produces hundreds of findings nobody reads. Tighten later.
import js from '@eslint/js'
import globals from 'globals'
import react from 'eslint-plugin-react'
import reactHooks from 'eslint-plugin-react-hooks'

export default [
    { ignores: ['dist/**', 'coverage/**', 'node_modules/**', 'playwright-report/**'] },

    js.configs.recommended,

    {
        files: ['**/*.{js,jsx}'],
        languageOptions: {
            ecmaVersion: 2023,
            sourceType: 'module',
            globals: { ...globals.browser, ...globals.es2021 },
            parserOptions: { ecmaFeatures: { jsx: true } },
        },
        settings: { react: { version: 'detect' } },
        plugins: { react, 'react-hooks': reactHooks },
        rules: {
            // ── Real bugs: these fail the build ──────────────────────────
            'react-hooks/rules-of-hooks': 'error',   // a hook in a branch IS a bug
            'react/jsx-key': 'error',            // missing keys cause silent list bugs
            'react/jsx-no-undef': 'error',
            'react/jsx-uses-vars': 'error',      // stops no-unused-vars misfiring on JSX
            'react/jsx-uses-react': 'off',       // new JSX transform
            'react/react-in-jsx-scope': 'off',   // ditto
            'no-unused-vars': ['warn', { argsIgnorePattern: '^_', varsIgnorePattern: '^_' }],

            'no-empty': ['error', { allowEmptyCatch: true }],  // `catch {}` is used deliberately

            // ── Advisories: visible as warnings, do NOT fail the build ───
            // These come from eslint-plugin-react-hooks v7 (React Compiler era).
            // They flag cascading-render patterns, not defects — the code works.
            // Fixing all 13 is a real refactor of effect bodies across the app
            // and does not belong in the PR that introduced linting. Kept at
            // `warn` so they stay on screen instead of being switched off:
            // a rule nobody can see is a rule nobody fixes.
            'react-hooks/exhaustive-deps': 'warn',
            'react-hooks/set-state-in-effect': 'warn',
            'react-hooks/preserve-manual-memoization': 'warn',
            'react-hooks/immutability': 'warn',
        },
    },

    {
        // Build/tooling configs run in Node, not the browser — `process` is real there.
        files: ['*.config.js', 'vite.config.js', 'playwright.config.js', 'tailwind.config.js',
                'postcss.config.js'],
        languageOptions: { globals: { ...globals.node } },
    },

    {
        // Test files run under Vitest/jsdom and Node globals.
        files: ['src/tests/**/*.{js,jsx}', '**/*.test.{js,jsx}', '**/*.spec.{js,jsx}'],
        languageOptions: { globals: { ...globals.node, ...globals.vitest } },
    },
]
