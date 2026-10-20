const $ = (id) => document.getElementById(id);
let state,
  audioUrl,
  busy = false,
  audioReady = false;
const csrf = document.querySelector('meta[name="csrf-token"]').content;

async function api(path, data) {
  const response = await fetch(
    path,
    data === undefined
      ? {}
      : {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf },
          body: JSON.stringify(data),
        },
  );
  const result = await response.json();
  if (!response.ok)
    throw new Error(
      result.error || 'Не удалось выполнить запрос. Попробуйте ещё раз.',
    );
  return result;
}

function screen(name) {
  $('audio').pause();
  ['start', 'quiz', 'result'].forEach((id) => ($(id).hidden = id !== name));
  $('error').textContent = '';
}

async function run(action) {
  if (busy) return;
  busy = true;
  $('error').textContent = '';
  try {
    await action();
  } catch (error) {
    $('error').textContent =
      error instanceof TypeError
        ? 'Не удалось связаться с сервером. Проверьте соединение и попробуйте ещё раз.'
        : error.message;
  } finally {
    busy = false;
  }
}

function choicesEnabled(enabled) {
  $('choices')
    .querySelectorAll('button')
    .forEach((button) => {
      // Answered buttons remain focusable for keyboard/touch text inspection.
      button.disabled = !enabled && !state.feedback;
      button.setAttribute('aria-disabled', String(!enabled));
    });
}

async function loadAudio() {
  audioReady = false;
  choicesEnabled(false);
  $('audio-status').textContent = 'Подготовка аудио…';
  const response = await fetch(state.question.audioUrl);
  if (!response.ok) {
    $('audio-status').textContent =
      'Аудио недоступно. Нажмите «Повторить», чтобы попробовать ещё раз.';
    throw new Error(
      'Не удалось подготовить аудио. Проверьте сервис озвучки и повторите воспроизведение.',
    );
  }
  if (audioUrl) URL.revokeObjectURL(audioUrl);
  audioUrl = URL.createObjectURL(await response.blob());
  $('audio').src = audioUrl;
  // Enable answers only after the browser has decoded playable audio.
  await new Promise((resolve, reject) => {
    $('audio').oncanplay = resolve;
    $('audio').onerror = () =>
      reject(new Error('Не удалось воспроизвести аудио. Попробуйте ещё раз.'));
    $('audio').load();
  });
  audioReady = true;
  choicesEnabled(!state.feedback);
  try {
    await $('audio').play();
    $('audio-status').textContent = '';
  } catch {
    $('audio-status').textContent =
      'Нажмите «Повторить», чтобы прослушать запись.';
  }
}

function feedback(value) {
  state.feedback = value;
  choicesEnabled(false);
  $('feedback').textContent = value.correctAnswerText;
  $('choice-text').textContent = '';
  $('choices')
    .querySelectorAll('button')
    .forEach((button) => {
      if (button.matches(':hover, :focus'))
        $('choice-text').textContent =
          value.choiceTexts[button.dataset.choiceId];
      if (button.dataset.choiceId !== value.selectedChoiceId) return;
      button.classList.add(value.isCorrect ? 'correct' : 'incorrect');
      const mark = document.createElement('span');
      mark.className = 'answer-mark';
      mark.textContent = value.isCorrect ? '✓' : '✕';
      mark.setAttribute('aria-hidden', 'true');
      button.append(mark);
      button.setAttribute(
        'aria-label',
        `${button.dataset.label}: ${value.isCorrect ? 'Верно' : 'Неверно'}`,
      );
    });
  $('next').disabled = false;
}

async function render(value) {
  state = value;
  if (value.complete) {
    screen('result');
    $('score').textContent = `${value.score} / ${value.total}`;
    return;
  }
  screen('quiz');
  $('progress').textContent = `${value.position} / ${value.total}`;
  $('meter').max = value.total;
  $('meter').value = value.position - 1;
  $('feedback').textContent = '';
  $('choice-text').textContent = '';
  $('next').disabled = true;
  $('next').textContent = 'Далее →';
  $('choices').dataset.layout = value.question.choiceLayout;
  $('choices').replaceChildren();
  const shortcuts =
    value.question.choiceLayout === 'short'
      ? ['Z', 'X', 'C', 'V']
      : ['A', 'S', 'Z', 'X'];
  for (const [index, choice] of value.question.choices.entries()) {
    const button = document.createElement('button');
    button.type = 'button';
    button.disabled = true;
    button.dataset.choiceId = choice.id;
    button.dataset.label = choice.label;
    button.dataset.shortcut = shortcuts[index];
    button.setAttribute('aria-keyshortcuts', shortcuts[index]);
    const shortcut = document.createElement('span');
    shortcut.className = 'choice-shortcut';
    shortcut.textContent = shortcuts[index];
    shortcut.setAttribute('aria-hidden', 'true');
    button.append(shortcut);
    const inspect = () => {
      if (state.feedback)
        $('choice-text').textContent = state.feedback.choiceTexts[choice.id];
    };
    button.onmouseenter = button.onfocus = inspect;
    button.onmouseleave = button.onblur = () => {
      $('choice-text').textContent = '';
    };
    if (choice.image) {
      const img = document.createElement('img');
      img.src = choice.image;
      img.alt = choice.label;
      button.append(img);
    } else {
      const label = document.createElement('span');
      label.textContent = choice.label;
      button.append(label);
    }
    button.onclick = () => {
      if (state.feedback) {
        inspect();
        return;
      }
      return run(async () => {
        choicesEnabled(false);
        try {
          const result = await api(`/api/attempts/${state.attemptId}/answers`, {
            questionId: state.question.id,
            choiceId: choice.id,
          });
          feedback(result);
        } catch (error) {
          choicesEnabled(audioReady && !state.feedback);
          throw error;
        }
      });
    };
    $('choices').append(button);
  }
  if (value.feedback) feedback(value.feedback);
  await loadAudio();
}

$('start-form').onsubmit = (event) => {
  event.preventDefault();
  run(async () => {
    $('begin').disabled = true;
    try {
      await render(
        await api('/api/attempts', {
          lessonId: new FormData(event.target).get('lessonId'),
          level: new FormData(event.target).get('level'),
        }),
      );
    } finally {
      $('begin').disabled = false;
    }
  });
};
$('replay').onclick = () =>
  run(async () => {
    if (!audioReady) await loadAudio();
    else {
      try {
        await $('audio').play();
      } catch {
        throw new Error('Не удалось воспроизвести аудио. Попробуйте ещё раз.');
      }
    }
  });
$('next').onclick = () =>
  run(async () => {
    $('next').disabled = true;
    try {
      await render(
        await api(`/api/attempts/${state.attemptId}/next`, {
          questionId: state.question.id,
        }),
      );
    } catch (error) {
      // Recover the server's current state if a successful response was lost.
      await render(await api(`/api/attempts/${state.attemptId}`));
      throw error;
    }
  });
$('ok').onclick = $('leave').onclick = () => {
  if (!busy) screen('start');
};

document.addEventListener('keydown', (event) => {
  if (
    $('quiz').hidden ||
    event.altKey ||
    event.ctrlKey ||
    event.metaKey ||
    event.shiftKey ||
    event.isComposing ||
    event.target.closest('input, textarea, select, [contenteditable="true"]')
  )
    return;
  const advance =
    event.code === 'Space' ||
    event.code === 'Enter' ||
    event.code === 'NumpadEnter';
  const shortcut = event.code.startsWith('Key') ? event.code.slice(3) : '';
  const button = advance
    ? $('next')
    : shortcut === 'R'
      ? $('replay')
      : [...$('choices').querySelectorAll('button')].find(
          (item) => item.dataset.shortcut === shortcut,
        );
  if (!button) return;
  // Suppress native Space/Enter activation even if focus remains on an answer.
  event.preventDefault();
  if (event.repeat || busy || button.disabled || (advance && !state.feedback))
    return;
  button.click();
});
