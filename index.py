from glob import glob
from pathlib import Path
import random
from aksharamukha import transliterate, GeneralMap
from flask import Flask, request, jsonify
from flask_cors import CORS
import unicodedataplus as unicodedata
from functools import cache

SCRIPT_THRESHOLD = 0.05

CONJUNCT_PROPS = {
    "Virama",
    "Invisible_Stacker",
    "Consonant_Dead",
    "Consonant_With_Stacker",
    "Consonant_Prefixed",
    "Consonant_Preceding_Repha",
    "Consonant_Initial_Postfixed",
    "Consonant_Succeeding_Repha",
    "Consonant_Subjoined",
    "Consonant_Medial",
    "Consonant_Final",
    "Consonant_Head_Letter",
    "Gemination_Mark",
}

INDEP_VOWEL_PROPS = {
    "Vowel_Independent",
}


def get_script_of_word(word):
    return {unicodedata.script(cp) for cp in word} - {"Common", "Inherited"}


locale_files = glob("data/wiktionary/*")
locales = [Path(d).name for d in locale_files]
wordlists = {}
for locale_file in locale_files:
    locale = Path(locale_file).name
    wordlists[locale] = {}
    forms = []
    # weights = []
    with open(locale_file) as datafile:
        for line in datafile.readlines():
            if not line:
                continue
            # try:
            #     form, weight = line.strip().split("\t")
            # except ValueError:
            form = line.strip()
            # weight = 1
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
            if script == "Mymr":
                script = "Burmese"
            if script == "Avst":
                script = "Avestan"
            if script not in wordlists[locale]:
                # wordlists[locale][script] = ([], [])
                wordlists[locale][script] = []
            wordlists[locale][script].append(form)
            # wordlists[locale][script][0].append(form)
            # wordlists[locale][script][1].append(int(weight))

script_map = {}
for locale in wordlists:
    script_map[locale] = []
    total_entries = 0
    for script in wordlists[locale]:
        # total_entries += len(wordlists[locale][script][0])
        total_entries += len(wordlists[locale][script])
    for script in wordlists[locale]:
        # if len(wordlists[locale][script][0]) / total_entries > SCRIPT_THRESHOLD:
        if len(wordlists[locale][script]) / total_entries > SCRIPT_THRESHOLD:
            script_map[locale].append(script)
app = Flask(__name__)
CORS(app)


def filter_wordlist(wordlist, filter_set, negative=False):
    output = []
    for word in wordlist:
        if negative:
            if any(unicodedata.indic_syllabic_category(c) in filter_set for c in word):
                continue
            else:
                output.append(word)
        else:
            if any(unicodedata.indic_syllabic_category(c) in filter_set for c in word):
                output.append(word)
    if not output:
        return wordlist
    return output


@app.route("/", methods=["POST", "GET"])
def serve_transl():
    from_script = request.json["from"]
    to_script = request.json["to"]
    text = request.json["text"]
    if text:
        return jsonify(
            transliterate.process(from_script, to_script, text, nativize=False)
        )
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
    positive_filter = set()
    negative_filter = set()
    if request.json["withConjuncts"] == 0:
        negative_filter.update(CONJUNCT_PROPS)
    elif request.json["withConjuncts"] == 2:
        positive_filter.update(CONJUNCT_PROPS)
    if request.json["withIndepVowels"] == 0:
        negative_filter.update(INDEP_VOWEL_PROPS)
    elif request.json["withIndepVowels"] == 2:
        positive_filter.update(INDEP_VOWEL_PROPS)
    wordlist = wordlists[lang][script]
    # randomized_wordlist = random.choices(wordlist[0], wordlist[1], k=500)
    randomized_wordlist = random.choices(wordlist, k=500)
    if script == from_script:
        from_wordlist = randomized_wordlist
    else:
        from_wordlist = [
            transliterate.process(script, from_script, word, nativize=False)
            for word in randomized_wordlist
        ]
    if positive_filter:
        from_wordlist = filter_wordlist(from_wordlist, positive_filter)
    if negative_filter:
        from_wordlist = filter_wordlist(from_wordlist, negative_filter, True)
    output = [
        [
            word,
            transliterate.process(from_script, to_script, word, nativize=False),
        ]
        for word in from_wordlist
    ]
    return jsonify([from_script, to_script, output])


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
