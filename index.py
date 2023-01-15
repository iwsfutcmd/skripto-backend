from glob import glob
from pathlib import Path
import random
from aksharamukha import transliterate, GeneralMap
from flask import Flask, request, jsonify
from flask_cors import CORS

locale_files = glob("data/*")
locales = [Path(d).name for d in locale_files]
wordlists = {}
for locale_file in locale_files:
    forms = []
    weights = []
    with open(locale_file) as datafile:
        for line in datafile.readlines():
            if not line: continue
            form, weight = line.strip().split("\t")
            forms.append(form)
            weights.append(int(weight))
    wordlists[Path(locale_file).name] = (forms, weights)

script_map = {
    "ta": "Tamil",
    "pa": "Gurmukhi",
    "te": "Telugu",
    "ml": "Malayalam",
    "mr": "Devanagari",
    "sa": "Latin",
    "si": "Sinhala",
    "th": "Thai",
}
app = Flask(__name__)
CORS(app)

@app.route("/", methods=["POST", "GET"])
def serve_transl():
    from_script = request.json["from"]
    to_script = request.json["to"]
    text = request.json["text"]
    if text:
        return jsonify(transliterate.process(from_script, script_map[to_script], text))
    else:
        return jsonify("")

@app.route("/scripts/latin")
def serve_latin_scripts():
    return jsonify(GeneralMap.LatinScripts + list(GeneralMap.semiticISO.keys()))

@app.route("/locales")
def serve_locales():
    return jsonify(locales)

@app.route("/wordlist", methods=["POST", "GET"])
def serve_wordlist():
    from_script = request.json["from"]
    to_script = request.json["to"]
    locale = request.json["locale"]
    randomized_wordlist = random.choices(wordlists[locale][0], weights=wordlists[locale][1], k=500)
    form_translit = [[form, transliterate.process(from_script, to_script, form)] for form in randomized_wordlist]
    return jsonify(form_translit)

if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=True)
