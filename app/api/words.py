from flask import abort, request, current_app
from flask_restx import Namespace, Resource, fields
import requests
import validators
import re

api = Namespace('words', 'Words related operations')

word_model = api.model('Word', {
    'word': fields.String,
    'counter': fields.Integer
})

counter_model = api.model('Counter', {
    'type': fields.String,
    'data': fields.String
})


class Word:
    def __init__(self, word, counter):
        self.word = word
        self.counter = counter


class Counter:
    def __init__(self, type, counter):
        self.type = type
        self.counter = counter


@api.route('/stats/<word>')
class WordStats(Resource):
    @api.marshal_with(word_model, code=200, description='Word count retrieved')
    def get(self, word):
        if word is None:
            abort(400)
        stats = query(word)
        return Word(word, stats)


@api.route('/counter', methods=['POST'])
class WordCounter(Resource):
    @api.response(code=200, description='Text processed')
    @api.expect(counter_model, validation=True)
    def post(self):
        content = request.get_json()
        if content['type'] == 'string':
            word_data = current_app.extensions['db'].open()
            process_string(content['data'], word_data)
            current_app.extensions['db'].persist(word_data)

        elif content['type'] == 'file':
            word_data = current_app.extensions['db'].open()
            try:
                with open(content['data']) as fh:
                    for line in fh:
                        process_string(line, word_data)
            except FileNotFoundError:
                abort(400)
            finally:
                current_app.extensions['db'].persist(word_data)

        elif content['type'] == 'url':
            word_data = current_app.extensions['db'].open()
            for line in make_request(content['data']):
                if line:
                    decoded_line = line.decode('utf-8')
                    process_string(decoded_line, word_data)
            current_app.extensions['db'].persist(word_data)

        else:
            abort(400)


def make_request(url):
    if not validators.url(url):
        abort(400)
    try:
        response = requests.get(url, stream=True)
        return response.iter_lines()
    except Exception:
        abort(500)


def process_string(words, word_data):
    for word in clean_text(words).split():
        try:
            word_data[word] += 1
        except KeyError:
            word_data[word] = 1


def query(key):
    word_data = current_app.extensions['db'].open()
    if clean_text(key) in word_data:
        return word_data[key]
    return 0


def clean_text(data):
    clean = data.lower()
    return re.sub(r'[^a-z ]', '', clean)
