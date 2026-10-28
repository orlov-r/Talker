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

test('Study opens static rows, preserves selection, plays audio and starts the quiz', async () => {
  const page = quizPage();
  const makeElement = (tag) => ({
    tag, children: [], attributes: {}, hidden: false,
    classList: { toggle(name, value) { this[name] = value; } },
    append(...children) { this.children.push(...children); },
    replaceChildren() { this.children = []; },
    setAttribute(name, value) { this.attributes[name] = value; },
    pause() {},
    play: async () => {},
  });
  for (const id of ['start', 'study', 'quiz', 'result', 'audio', 'study-audio', 'study-words']) {
    page.elements.set(id, makeElement(id));
    page.elements.get(id).hidden = id !== 'start';
  }
  const document = vm.runInContext('document', page.context);
  document.createElement = makeElement;
  const requests = [];
  let failAudio = false;
  let studyWords = [
    { text: 'ძაღლი', translation: 'собака', level: 1, image: '/static/choices/dog.jpg', audioUrl: '/study/0/audio' },
    { text: 'კატა', translation: 'кошка', level: 2, audioUrl: '/study/1/audio' },
  ];
  page.context.URLSearchParams = URLSearchParams;
  page.context.FormData = class {
    get(key) { return { lessonId: 'animals', voice: 'rhvoice', level: 'hard' }[key]; }
  };
  page.context.URL = { createObjectURL: () => 'blob:study', revokeObjectURL() {} };
  page.context.fetch = async (path) => {
    requests.push(path);
    return path.includes('/audio')
      ? { ok: !failAudio, blob: async () => ({}) }
      : { ok: true, json: async () => ({ title: 'Animals', words: studyWords }) };
  };
  await page.elements.get('open-study').onclick();
  assert.equal(requests[0], '/api/lessons/animals/study?level=hard&voice=rhvoice');
  assert.equal(page.elements.get('start').hidden, true);
  assert.equal(page.elements.get('study').hidden, false);
  const rows = page.elements.get('study-words').children;
  assert.equal(rows.length, 2);
  assert.equal(rows[0].classList['study-basic'], true);
  assert.equal(rows[1].classList['study-basic'], false);
  assert.equal(page.elements.get('study-image-heading').hidden, false);
  assert.equal(page.elements.get('study-level-hint').hidden, false);
  assert.equal(rows[0].children[0].children[0].disabled, true);
  assert.equal(rows[0].children[1].lang, 'ka');
  const speaker = rows[0].children[3].children[0];
  await speaker.onclick();
  assert.equal(page.elements.get('study-audio').src, 'blob:study');
  failAudio = true;
  await speaker.onclick();
  assert.match(page.elements.get('error').textContent, /аудио/);
  failAudio = false;
  await speaker.onclick();
  assert.equal(page.elements.get('error').textContent, '');
  let starts = 0;
  page.elements.get('start-form').requestSubmit = () => starts++;
  page.elements.get('study-begin').onclick();
  assert.equal(starts, 1);
  page.elements.get('study-back').onclick();
  assert.equal(page.elements.get('start').hidden, false);
  assert.equal(page.elements.get('study').hidden, true);
  studyWords = studyWords.map(({ image, ...word }) => ({ ...word, level: 1 }));
  await page.elements.get('open-study').onclick();
  assert.equal(page.elements.get('study-image-heading').hidden, true);
  assert.equal(page.elements.get('study-level-hint').hidden, true);
  for (const row of page.elements.get('study-words').children) {
    assert.equal(row.children.length, 3);
    assert.equal(row.children[0].lang, 'ka');
    assert.equal(row.classList['study-basic'], false);
  }
});
