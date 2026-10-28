// Run from the repository root: node --test web/test_shortcuts.js
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { test } = require('node:test');
const vm = require('node:vm');

function quizPage(answered = false) {
  const elements = new Map();
  const clicks = [];
  let keydown;
  const document = {
    getElementById(id) {
      if (!elements.has(id))
        elements.set(id, {
          hidden: id === 'start' || id === 'result',
          disabled: id === 'next' && !answered,
          attributes: {},
          setAttribute(name, value) {
            this.attributes[name] = value;
          },
          closest: () => null,
          focus() {},
          scrollIntoView() {},
          querySelectorAll: () => [],
        });
      return elements.get(id);
    },
    querySelector: () => ({ content: 'test-token' }),
    addEventListener(name, handler) {
      if (name === 'keydown') keydown = handler;
    },
  };
  const context = vm.createContext({ document });
  vm.runInContext(readFileSync(`${__dirname}/static/app.js`, 'utf8'), context);
  vm.runInContext(`state = { feedback: ${answered ? '{}' : 'null'} };`, context);
  for (const id of ['replay', 'next'])
    document.getElementById(id).click = () => clicks.push(id);
  return {
    context,
    elements,
    clicks,
    press(code, overrides = {}) {
      keydown({
        code,
        target: { closest: () => null },
        preventDefault() {},
        ...overrides,
      });
    },
  };
}

test('Space and R replay before answering; Enter cannot advance', () => {
  const page = quizPage();
  page.press('Space');
  page.press('KeyR');
  page.press('Enter');
  page.press('NumpadEnter');
  assert.deepEqual(page.clicks, ['replay', 'replay']);
});

test('Space and both Enter keys advance after answering; R still replays', () => {
  const page = quizPage(true);
  for (const key of ['Space', 'Enter', 'NumpadEnter', 'KeyR']) page.press(key);
  assert.deepEqual(page.clicks, ['next', 'next', 'next', 'replay']);
});

test('Replay shortcuts respect repeat, modifiers, inputs and busy requests', () => {
  const page = quizPage();
  for (const code of ['Space', 'KeyR']) {
    for (const flag of [
      'repeat',
      'altKey',
      'ctrlKey',
      'metaKey',
      'shiftKey',
      'isComposing',
    ])
      page.press(code, { [flag]: true });
    page.press(code, { target: { closest: () => ({}) } });
  }
  vm.runInContext('busy = true;', page.context);
  page.press('Space');
  page.press('KeyR');
  assert.deepEqual(page.clicks, []);
});

test('Replay hint and accessible shortcuts reflect answer state', () => {
  const page = quizPage();
  vm.runInContext('replayShortcut();', page.context);
  assert.equal(
    page.elements.get('replay-hint').textContent,
    'R / Пробел — повторить',
  );
  assert.equal(
    page.elements.get('replay').attributes['aria-keyshortcuts'],
    'R Space',
  );
  vm.runInContext('state.feedback = {}; replayShortcut();', page.context);
  assert.equal(page.elements.get('replay-hint').textContent, 'R — повторить');
  assert.equal(page.elements.get('replay').attributes['aria-keyshortcuts'], 'R');
});
