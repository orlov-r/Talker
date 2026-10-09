const $ = id => document.getElementById(id);
let state, audioUrl, busy = false, audioReady = false;
const csrf = document.querySelector('meta[name="csrf-token"]').content;

async function api(path, data) {
  const response = await fetch(path, data === undefined ? {} : {
    method: 'POST', headers: {'Content-Type': 'application/json', 'X-CSRF-Token': csrf},
    body: JSON.stringify(data)
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || 'Request failed. Please retry.');
  return result;
}

function screen(name) {
  $('audio').pause();
  ['start', 'quiz', 'result'].forEach(id => $(id).hidden = id !== name);
  $('error').textContent = '';
}

async function run(action) {
  if (busy) return;
  busy = true;
  $('error').textContent = '';
  try { await action(); } catch (error) { $('error').textContent = error.message; }
  finally { busy = false; }
}

function choicesEnabled(enabled) {
  $('choices').querySelectorAll('button').forEach(button => button.disabled = !enabled);
}

async function loadAudio() {
  audioReady = false;
  choicesEnabled(false);
  $('audio-status').textContent = 'Preparing audio…';
  const response = await fetch(state.question.audioUrl);
  if (!response.ok) {
    $('audio-status').textContent = 'Audio unavailable. Use Play / replay to retry.';
    throw new Error('Could not prepare audio. Check the speech service, then retry playback.');
  }
  if (audioUrl) URL.revokeObjectURL(audioUrl);
  audioUrl = URL.createObjectURL(await response.blob());
  $('audio').src = audioUrl;
  // Enable answers only after the browser has decoded playable audio.
  await new Promise((resolve, reject) => {
    $('audio').oncanplay = resolve;
    $('audio').onerror = () => reject(new Error('Audio could not be played. Retry playback.'));
    $('audio').load();
  });
  audioReady = true;
  choicesEnabled(!state.feedback);
  try { await $('audio').play(); $('audio-status').textContent = 'Replay as often as you like.'; }
  catch { $('audio-status').textContent = 'Press Play / replay to listen.'; }
}

function feedback(value) {
  state.feedback = value;
  choicesEnabled(false);
  $('feedback').textContent = `${value.isCorrect ? 'Correct!' : 'Not quite.'} Answer: ${value.correctAnswerText}`;
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
  $('progress').textContent = `Question ${value.position} of ${value.total}`;
  $('meter').max = value.total;
  $('meter').value = value.position - 1;
  $('feedback').textContent = '';
  $('next').disabled = true;
  $('next').textContent = value.position === value.total ? 'See results →' : 'Next question →';
  $('choices').replaceChildren();
  for (const choice of value.question.choices) {
    const button = document.createElement('button');
    button.type = 'button'; button.textContent = choice.label; button.disabled = true;
    button.onclick = () => run(async () => {
      choicesEnabled(false);
      try {
        const result = await api(`/api/attempts/${state.attemptId}/answers`, {
          questionId: state.question.id, choiceId: choice.id
        });
        button.classList.add('selected'); feedback(result);
      } catch (error) { choicesEnabled(audioReady && !state.feedback); throw error; }
    });
    $('choices').append(button);
  }
  if (value.feedback) feedback(value.feedback);
  await loadAudio();
}

$('start-form').onsubmit = event => {
  event.preventDefault();
  run(async () => {
    $('begin').disabled = true;
    try { await render(await api('/api/attempts', {
      lessonId: 'basics', level: new FormData(event.target).get('level')
    })); } finally { $('begin').disabled = false; }
  });
};
$('replay').onclick = () => run(async () => {
  if (!audioReady) await loadAudio(); else await $('audio').play();
});
$('next').onclick = () => run(async () => {
  $('next').disabled = true;
  try { await render(await api(`/api/attempts/${state.attemptId}/next`, {questionId: state.question.id})); }
  catch (error) {
    // Recover the server's current state if a successful response was lost.
    await render(await api(`/api/attempts/${state.attemptId}`));
    throw error;
  }
});
$('ok').onclick = $('leave').onclick = () => { if (!busy) screen('start'); };
