from glob import glob
from pathlib import Path
import random
from aksharamukha import transliterate, GeneralMap
from flask import Flask, request, jsonify
from flask_cors import CORS
import unicodedataplus as unicodedata


def get_script_of_word(word):
    return {unicodedata.script(cp) for cp in word} - {"Common", "Inherited"}


locale_files = glob("data/wiktionary/*")
locales = [Path(d).name for d in locale_files]
wordlists = {}
for locale_file in locale_files:
    locale = Path(locale_file).name
    wordlists[locale] = {}
    forms = []
    weights = []
    with open(locale_file) as datafile:
        for line in datafile.readlines():
            if not line:
                continue
            try:
                form, weight = line.strip().split("\t")
            except ValueError:
                form = line.strip()
                weight = 1
            scripts = get_script_of_word(form)
            if len(scripts) == 1:
                script = scripts.pop()
                unnormalized_script = script
                script = script.replace("_", "")
                if script not in GeneralMap.IndicScripts:
                    script = unicodedata.property_value_aliases["script"][
                        unnormalized_script
                    ][0]
            else:
                script = "Zyyy"
            if script == "Syrc":
                script = "Syre"
            if script not in wordlists[locale]:
                wordlists[locale][script] = ([], [])
            wordlists[locale][script][0].append(form)
            wordlists[locale][script][1].append(int(weight))

script_map = {}
for locale in wordlists:
    script_map[locale] = []
    total_entries = 0
    for script in wordlists[locale]:
        total_entries += len(wordlists[locale][script][0])
    for script in wordlists[locale]:
        if len(wordlists[locale][script][0]) / total_entries > 0.1:
            script_map[locale].append(script)
app = Flask(__name__)
CORS(app)


@app.route("/", methods=["POST", "GET"])
def serve_transl():
    from_script = request.json["from"]
    to_script = request.json["to"]
    text = request.json["text"]
    if text:
        return jsonify(transliterate.process(from_script, to_script, text))
    else:
        return jsonify("")


@app.route("/scripts")
def serve_scripts():
    return jsonify(
        list(
            set(
                GeneralMap.LatinScripts
                + GeneralMap.MainIndic
                + GeneralMap.EastIndic
                + GeneralMap.NonIndic
                + GeneralMap.SemiticScripts
                + GeneralMap.Roman
                + list(GeneralMap.semiticISO.keys())
            )
        )
    )


@app.route("/locales")
def serve_locales():
    return jsonify(list(script_map.items()))


@app.route("/wordlist", methods=["POST", "GET"])
def serve_wordlist():
    to_script = request.json["to"]
    lang = request.json["lang"]
    script = request.json["script"]
    from_script = (
        script if request.json["from"] == "autodetect" else request.json["from"]
    )
    randomized_wordlist = random.choices(
        wordlists[lang][script][0], weights=wordlists[lang][script][1], k=500
    )
    form_translit = [
        [
            transliterate.process(script, from_script, form),
            transliterate.process(script, to_script, form),
        ]
        for form in randomized_wordlist
    ]
    return jsonify([from_script, to_script, form_translit])


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
