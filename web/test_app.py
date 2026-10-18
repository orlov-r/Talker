"""Quiz contract checks using a simulated WAV, not the real Natia voice."""
import io
import json
import re
import unittest
import wave
from concurrent.futures import ThreadPoolExecutor
from web.app import create_app
from web.audio import AudioCache, cache_key
from web.content import validate, questions


def wav_bytes(*args):
    output = io.BytesIO()
    with wave.open(output, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(b'\0\0' * 160)
    return output.getvalue()


class QuizTests(unittest.TestCase):
    def setUp(self):
        self.calls = []

        def synth(text, rate, url):
            self.calls.append((text, rate))
            return wav_bytes()

        self.app = create_app({'TESTING': True, 'SECRET_KEY': 'test', 'SYNTHESIZER': synth})
        self.client = self.app.test_client()
        self.client.get('/')
        with self.client.session_transaction() as session:
            self.token = session['csrf']

    def post(self, path, data):
        return self.client.post(path, json=data, headers={'X-CSRF-Token': self.token})

    def start(self, level='easy'):
        response = self.post('/api/attempts', {'lessonId': 'basics', 'level': level})
        self.assertEqual(response.status_code, 201)
        return response.json

    def answer(self, state, choice=None):
        question = state['question']
        return self.post(f"/api/attempts/{state['attemptId']}/answers", {
            'questionId': question['id'], 'choiceId': choice or question['choices'][0]['id']})

    def advance(self, state):
        return self.post(f"/api/attempts/{state['attemptId']}/next", {'questionId': state['question']['id']})

    def test_levels_and_complete_score(self):
        for level, count, rate in [('easy', 7, 80), ('medium', 10, 100), ('hard', 15, 120)]:
            state = self.start(level)
            aid = state['attemptId']
            self.assertEqual(state['total'], count)
            self.assertEqual(self.client.get(f'/api/attempts/{aid}/result').status_code, 409)
            for i in range(count):
                serialized = json.dumps(state)
                self.assertNotIn('speechText', serialized)
                self.assertNotIn('correctChoiceId', serialized)
                self.assertEqual(len(state['question']['choices']), 4)
                self.assertEqual(self.client.get(state['question']['audioUrl']).mimetype, 'audio/wav')
                q = self.app.extensions['attempts'][aid]['questions'][i]
                self.assertEqual(q['rate'], rate)
                first = self.answer(state, q['correctChoiceId'])
                self.assertTrue(first.json['isCorrect'])
                other = next(c['id'] for c in q['choices'] if c['id'] != q['correctChoiceId'])
                self.assertEqual(self.answer(state, other).json, first.json)
                previous = state
                state = self.advance(state).json
                self.assertEqual(self.advance(previous).status_code, 409)
            self.assertEqual(state['score'], count)
            self.assertTrue(state['complete'])
            self.assertEqual(self.client.get(f'/api/attempts/{aid}/result').json['score'], count)

    def test_wrong_answer_and_order(self):
        state = self.start()
        self.assertEqual(self.answer(state).status_code, 409)
        self.assertEqual(self.advance(state).status_code, 409)
        self.client.get(state['question']['audioUrl'])
        self.assertEqual(self.answer(state, 'unknown').status_code, 409)
        self.assertEqual(self.post(f"/api/attempts/{state['attemptId']}/answers",
                                  {'questionId': 'q2', 'choiceId': 'hello'}).status_code, 409)
        wrong = next(c['id'] for c in state['question']['choices'] if c['id'] != 'hello')
        response = self.answer(state, wrong)
        self.assertEqual(response.json['selectedChoiceId'], wrong)
        self.assertEqual(self.client.get(f"/api/attempts/{state['attemptId']}").json['feedback'], response.json)
        self.assertFalse(response.json['isCorrect'])
        self.assertEqual(self.app.extensions['attempts'][state['attemptId']]['score'], 0)

    def test_ownership_expiry_and_private_content(self):
        state = self.start()
        other = self.app.test_client()
        other.get('/')
        with other.session_transaction() as session:
            token = session['csrf']
        base = f"/api/attempts/{state['attemptId']}"
        for path in [base, base + '/result', state['question']['audioUrl']]:
            self.assertEqual(other.get(path).status_code, 404)
        for path in [base + '/answers', base + '/next']:
            self.assertEqual(other.post(path, json={}, headers={'X-CSRF-Token': token}).status_code, 404)
        self.assertEqual(self.client.get('/lessons/basics.json').status_code, 404)
        self.app.extensions['attempts'][state['attemptId']]['expires'] = 0
        self.assertEqual(self.client.get(base).status_code, 404)

    def test_validation_csrf_bounds(self):
        self.assertEqual(self.client.post('/api/attempts', json={}).status_code, 403)
        for data in [[], {}, {'lessonId': 'basics', 'level': []}, {'lessonId': 'other', 'level': 'easy'}]:
            self.assertEqual(self.post('/api/attempts', data).status_code, 400)
        self.assertEqual(self.post('/api/attempts', {'padding': 'x' * 5000}).status_code, 413)

    def test_stable_generation_audio_cache_and_version(self):
        state = self.start()
        self.client.get(state['question']['audioUrl'])
        self.client.get(state['question']['audioUrl'])
        self.assertEqual(len(self.calls), 1)
        self.answer(state)
        dynamic = self.advance(state).json
        before = self.client.get(f"/api/attempts/{state['attemptId']}").json
        self.client.get(dynamic['question']['audioUrl'])
        self.client.get(dynamic['question']['audioUrl'])
        self.assertEqual(before, self.client.get(f"/api/attempts/{state['attemptId']}").json)
        self.assertEqual(len(self.calls), 2)
        self.app.config['SYNTHESIS_VERSION'] = 'changed-build'
        current = self.client.get(f"/api/attempts/{state['attemptId']}").json
        self.assertNotEqual(current['question']['audioUrl'], dynamic['question']['audioUrl'])
        self.assertEqual(self.client.get(dynamic['question']['audioUrl']).status_code, 404)
        self.client.get(current['question']['audioUrl'])
        self.assertEqual(len(self.calls), 3)

    def test_audio_failure_retry_does_not_score_or_advance(self):
        state = self.start()

        def fail(*args):
            raise TimeoutError('simulated timeout')

        self.app.config['SYNTHESIZER'] = fail
        with self.assertLogs(self.app.logger, level='ERROR'):
            self.assertEqual(self.client.get(state['question']['audioUrl']).status_code, 502)
        self.assertEqual(self.answer(state).status_code, 409)
        self.assertEqual(self.advance(state).status_code, 409)
        self.app.config['SYNTHESIZER'] = wav_bytes
        self.assertEqual(self.client.get(state['question']['audioUrl']).status_code, 200)
        self.assertEqual(self.answer(state).status_code, 200)

    def test_capacity(self):
        self.app.config['MAX_ATTEMPTS'] = 0
        self.assertEqual(self.post('/api/attempts', {'lessonId': 'basics', 'level': 'easy'}).status_code, 503)

    def test_page_and_assets(self):
        html = self.client.get('/').get_data(as_text=True)
        self.assertIn('<html lang="ru">', html)
        self.assertIn('Вопросов: 15', html)
        self.assertIn('Приветствия и числа', html)
        for path in re.findall(r'(?:src|href)="(/static/[^\"]+)"', html):
            with self.client.get(path) as response:
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.mimetype, 'text/javascript' if path.endswith('.js') else 'text/css')


class ContentAndCacheTests(unittest.TestCase):
    def test_defaults_and_bad_definitions(self):
        q = {'speechText': ' one ', 'choices': [{'id': str(i), 'label': name}
             for i, name in enumerate(['one', 'two', 'three', 'four', 'five'])]}
        resolved = validate(q)
        self.assertEqual(resolved['correctChoiceId'], '0')
        self.assertEqual(resolved['correctAnswerText'], ' one ')
        for changed in [dict(q, speechText='missing'), dict(q, choices=q['choices'][:3]),
                        dict(q, correctChoiceId='missing'), dict(q, correctAnswerText='')]:
            with self.assertRaises(ValueError):
                validate(changed)

    def test_choice_sampling_and_layout(self):
        for _ in range(20):
            for q in questions('easy'):
                self.assertEqual(len(q['choices']), 4)
                self.assertEqual(len({c['id'] for c in q['choices']}), 4)
                self.assertIn(q['correctChoiceId'], [c['id'] for c in q['choices']])
                self.assertEqual(q['choiceLayout'], 'short' if int(q['id'][1:]) % 2 == 0 else 'long')
        q = {'speechText': '0', 'choices': [{'id': str(i), 'label': str(i)} for i in range(4)]}
        self.assertEqual(validate(q)['choiceLayout'], 'long')
        with self.assertRaises(ValueError):
            validate(dict(q, choiceLayout='wide'))
        q['choices'][0]['image'] = '/static/choices/zero.png'
        self.assertEqual(validate(q)['choices'][0]['image'], '/static/choices/zero.png')
        q['choices'][0]['image'] = 'https://example.com/zero.png'
        with self.assertRaises(ValueError):
            validate(q)

    def test_cache_bounds_concurrent_misses_and_keys(self):
        cache, calls = AudioCache(limit=2), []

        def produce():
            calls.append(1)
            return b'audio'

        with ThreadPoolExecutor(max_workers=4) as pool:
            self.assertEqual(list(pool.map(lambda _: cache.get('one', produce), range(8))), [b'audio'] * 8)
        self.assertEqual(len(calls), 1)
        cache.get('two', produce)
        cache.get('three', produce)
        self.assertEqual(len(cache.entries), 2)
        self.assertNotIn('one', cache.entries)
        self.assertNotEqual(cache_key('a', 80, 'v1'), cache_key('a', 100, 'v1'))
        self.assertNotEqual(cache_key('a', 80, 'v1'), cache_key('a', 80, 'v2'))


if __name__ == '__main__':
    unittest.main()
