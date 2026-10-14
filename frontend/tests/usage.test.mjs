import test from 'node:test';
import assert from 'node:assert/strict';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { createServer } from 'vite';

const vite = await createServer({ server: { middlewareMode: true }, appType: 'custom' });
test.after(async () => { await vite.close(); });

test('Codex persisted sessions have a readable source label', async () => {
  const { harnessLabel } = await vite.ssrLoadModule('/src/theme.js');
  assert.equal(harnessLabel('codex_cli'), 'Codex');
});

test('reasoning remains included in output percentages', async () => {
  const { default: ContextBreakdown } = await vite.ssrLoadModule('/src/components/ContextBreakdown.jsx');
  const summary = { input_tokens: 40, output_tokens: 20, cache_read_tokens: 30, cache_creation_tokens: 10, reasoning_tokens: 10 };
  const html = renderToStaticMarkup(React.createElement(ContextBreakdown, { summary }));
  assert.match(html, /20\.0%/);
  assert.match(html, /Reasoning \(included in output\)/);
});
