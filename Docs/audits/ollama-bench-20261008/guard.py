"""Garde qualité de task-355 : ancien contre nouveau gabarit d'étiquetage, sur qwen2.5:14b local.

Usage : python -I guard.py PORT CORPUS_DIR OLD_CS NEW_CS [N_MIN] [CONC]

- OLD_CS / NEW_CS : deux versions de EmailTaggingService.cs (ancienne : `git show origin/develop:…`).
  Les gabarits sont reconstruits depuis les littéraux bruts C#, selon la règle du langage
  (indentation du délimiteur fermant retirée de chaque ligne), puis concaténés comme dans le code.
- CORPUS_DIR : JEUX_TESTS_FULL. Chaque document CDA distinct (fichier XML, ou XML d'un ZIP
  IHE_XDM, dédoublonnés sur le texte) donne une entrée : titre en sujet, texte
  narratif des sections en corps, type de document tiré du code LOINC (table de
  CDADocumentHelper.GetCdaDocumentType), contenu tronqué à 5 000 caractères comme en production.
  Si le corpus donne moins de N_MIN entrées, les documents longs fournissent une seconde fenêtre
  (caractères 5 000 à 10 000), qui est un contenu distinct.
- Trois passes : A (ancien), B (nouveau), A2 (ancien, rejouée) pour mesurer le bruit propre au
  modèle (température par défaut, comme en production).
- Lecture des réponses identique à ParseTagsFromResponse : du premier « { » au dernier « } »,
  JSON illisible = « illisible » (le mail reste sans étiquette), étiquette hors des trois libellés
  = aucune étiquette.

Aucun contenu de document n'est écrit : la sortie ne porte que des comptes.
"""
import hashlib, json, os, re, sys, threading, time, urllib.request, zipfile
import xml.etree.ElementTree as ET

PORT, CORPUS, OLD_CS, NEW_CS = int(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4]
N_MIN = int(sys.argv[5]) if len(sys.argv) > 5 else 200
CONC = int(sys.argv[6]) if len(sys.argv) > 6 else 8
MAX_CHARS = 5000
LABELS = ["Très urgent", "Urgent", "Important"]
NS = {"h": "urn:hl7-org:v3"}

LOINC = {}
for codes, kind in [
    ("SYNTH 34133-9 60591-5 78489-2 57057-2 89235-6", "Synth"), ("11502-2", "Bio"),
    ("11369-6 87273-9", "Vaccination"), ("57833-6", "Prescription"), ("18748-4 55115-0", "Imagerie"),
    ("11488-4 74207-2 78513-9", "Consultation"), ("18842-5 34105-7 75496-0", "Hospitalisation"),
    ("51969-4", "Genetique"), ("56445-0 60593-1", "Pharmacie"), ("11504-8 77436-4", "Operatoire"),
    ("11526-1", "Anatomopathologie"), ("28570-0", "Procedure"), ("34117-2 28626-0", "HistoirePhysique"),
    ("15507-7", "Urgences"), ("CERT_DECL", "Certificat"), ("11490-0 18761-7", "LettreLiaison"),
    ("85208-7", "Telemedecine"), ("REMB", "Remboursement")]:
    for c in codes.split():
        LOINC[c] = kind


def raw_literals(src, name):
    """Rend la valeur de la constante `name` : littéraux bruts et identifiants concaténés."""
    m = re.search(r"const string " + name + r" = (.*?);\n", src, re.S)
    expr, out = m.group(1), []
    pos = 0
    while pos < len(expr):
        if expr.startswith('"""', pos):
            end = expr.index('"""', pos + 3)
            body = expr[pos + 3:end]
            lines = body.split("\n")[1:]          # la ligne d'ouverture est vide
            indent = lines[-1]                    # ligne du délimiteur fermant : son indentation
            assert indent.strip() == "", name
            content = [l[len(indent):] if l.startswith(indent) else l.strip() for l in lines[:-1]]
            out.append("\n".join(content))
            pos = end + 3
        elif expr[pos].isalpha():
            ident = re.match(r"\w+", expr[pos:]).group(0)
            out.append(raw_literals(src, ident))
            pos += len(ident)
        else:
            pos += 1
    return "".join(out)


def template(cs_path):
    src = open(cs_path, encoding="utf-8").read().replace("\r\n", "\n")
    return raw_literals(src, "TaggingPromptTemplate")


def cda_documents():
    """Les CDA du corpus : fichiers XML, et XML contenus dans les ZIP (IHE_XDM)."""
    for root, _, files in os.walk(CORPUS):
        for f in sorted(files):
            path = os.path.join(root, f)
            if f.upper().endswith(".XML") and f.upper() != "METADATA.XML":
                with open(path, "rb") as h:
                    yield h.read()
            elif f.upper().endswith(".ZIP"):
                try:
                    with zipfile.ZipFile(path) as z:
                        for name in sorted(z.namelist()):
                            if name.upper().endswith(".XML") and not name.upper().endswith("METADATA.XML"):
                                yield z.read(name)
                except zipfile.BadZipFile:
                    continue


def cda_entries():
    entries, seen = [], set()
    for raw in cda_documents():
        try:
            doc = ET.fromstring(raw)
        except ET.ParseError:
            continue
        if not doc.tag.endswith("ClinicalDocument"):
            continue
        title = " ".join((doc.findtext("h:title", "", NS) or "").split())
        code = doc.find("h:code", NS)
        loinc = code.get("code") if code is not None else None
        texts = []
        for section in doc.iter("{urn:hl7-org:v3}section"):
            st = section.findtext("h:title", "", NS)
            body = section.find("h:text", NS)
            if st:
                texts.append(st.strip())
            if body is not None:
                texts.append(" ".join(" ".join(body.itertext()).split()))
        text = "\n".join(t for t in texts if t)
        if not text:
            continue
        digest = hashlib.sha256(text.encode()).hexdigest()
        if digest in seen:
            continue
        seen.add(digest)
        mail = None
        for tel in doc.iterfind("h:author/h:assignedAuthor/h:telecom", NS):
            if (tel.get("value") or "").startswith("mailto:"):
                mail = tel.get("value")[7:]
                break
        entries.append({"type": LOINC.get(loinc, "Document"), "sender": mail or "Inconnu",
                        "title": title, "texts": [t for t in texts if t],
                        "full": f"{title}\n\n{text}"})
    return entries


def inputs():
    """Un mail par document ; puis, pour atteindre N_MIN, des contenus DISTINCTS du même corpus :
    la suite des documents longs (au-delà des 5 000 caractères lus), puis la seconde moitié des
    sections des documents qui en ont au moins quatre (titre + sections, comme un extrait)."""
    base = cda_entries()
    items = [dict(e, content=e["full"][:MAX_CHARS], window=1) for e in base]
    for e in sorted(base, key=lambda e: -len(e["full"])):
        if len(items) >= N_MIN:
            break
        if len(e["full"]) > MAX_CHARS + 500:
            items.append(dict(e, content=e["full"][MAX_CHARS:2 * MAX_CHARS], window=2))
    for e in sorted(base, key=lambda e: -len(e["texts"])):
        if len(items) >= N_MIN or len(e["texts"]) < 4:
            break
        half = e["texts"][len(e["texts"]) // 2:]
        excerpt = (e["title"] + "\n\n" + "\n".join(half))[:MAX_CHARS]
        if all(excerpt != i["content"] for i in items):
            items.append(dict(e, content=excerpt, window=3))
    return base, items


def parse(reply):
    s = reply.strip()
    i, j = s.find("{"), s.rfind("}")
    if i >= 0 and j > i:
        s = s[i:j + 1]
    try:
        d = json.loads(s)
    except ValueError:
        return "illisible"
    if not isinstance(d, dict):
        return "illisible"
    tag = {k.lower(): v for k, v in d.items()}.get("tag")
    if not isinstance(tag, str):
        return "aucune"
    return next((l for l in LABELS if l.lower() == tag.strip().lower()), "aucune")


def run(tpl, items, options=None):
    results = [None] * len(items)
    queue, lock = list(range(len(items))), threading.Lock()

    def worker():
        while True:
            with lock:
                if not queue:
                    return
                k = queue.pop(0)
            it = items[k]
            prompt = (tpl.replace("{{$documentType}}", it["type"])
                         .replace("{{$senderEmail}}", it["sender"])
                         .replace("{{$content}}", it["content"]))
            payload = {"model": "qwen2.5:14b", "stream": False,
                       "messages": [{"role": "user", "content": prompt}]}
            if options:
                payload["options"] = options
            body = json.dumps(payload).encode()
            req = urllib.request.Request(f"http://127.0.0.1:{PORT}/api/chat", body,
                                         {"Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=600) as r:
                    results[k] = parse(json.loads(r.read())["message"]["content"])
            except Exception:  # noqa: BLE001 — l'échec est compté, jamais affiché
                results[k] = "erreur"

    t0 = time.perf_counter()
    threads = [threading.Thread(target=worker) for _ in range(CONC)]
    for t in threads: t.start()
    for t in threads: t.join()
    return results, time.perf_counter() - t0


def effective(c):
    # Effet en production : illisible et aucune laissent toutes deux le mail sans étiquette.
    return "aucune" if c == "illisible" else c


def compare(a, b):
    n = len(a)
    strict = sum(1 for x, y in zip(a, b) if x == y)
    eff = sum(1 for x, y in zip(a, b) if effective(x) == effective(y))
    return {"strict_pct": round(100 * strict / n, 1), "etiquette_pct": round(100 * eff / n, 1),
            "discordants": n - eff}


def dist(r):
    return {k: r.count(k) for k in LABELS + ["aucune", "illisible", "erreur"]}


old_tpl, new_tpl = template(OLD_CS), template(NEW_CS)
assert old_tpl != new_tpl and sorted(old_tpl.splitlines()) == sorted(new_tpl.splitlines()), \
    "les deux gabarits doivent porter les mêmes lignes, dans un autre ordre"
base, items = inputs()
print(json.dumps({"documents_cda": len(base), "entrees": len(items),
                  "suites_documents_longs": sum(1 for i in items if i["window"] == 2),
                  "extraits_seconde_moitie": sum(1 for i in items if i["window"] == 3),
                  "types": {t: sum(1 for i in items if i["type"] == t) for t in sorted({i["type"] for i in items})}},
                 ensure_ascii=False))
# Passes : GUARD_PASSES="A,B,A2" par défaut. Une passe nommée A… joue l'ancien gabarit, B… le
# nouveau ; un suffixe « 0 » (A0, B0) la joue à température 0 et graine fixe, pour isoler l'effet de
# l'ordre du bruit d'échantillonnage. Sans suffixe : options par défaut du serveur, comme en production.
RANK = {"Très urgent": 3, "Urgent": 2, "Important": 1, "aucune": 0, "illisible": 0, "erreur": -1}
passes, durations = {}, {}
for name in os.environ.get("GUARD_PASSES", "A,B,A2").split(","):
    tpl = old_tpl if name.startswith("A") else new_tpl
    options = {"temperature": 0, "seed": 42} if name.endswith("0") else None
    passes[name], d = run(tpl, items, options)
    durations[name] = round(d)


def moves(a, b):
    up = sum(1 for x, y in zip(a, b) if RANK[effective(y)] > RANK[effective(x)])
    down = sum(1 for x, y in zip(a, b) if RANK[effective(y)] < RANK[effective(x)])
    return {"montees": up, "descentes": down}


names = list(passes)
print(json.dumps({
    "distributions": {n: dist(r) for n, r in passes.items()},
    "paires": {f"{x}_vs_{y}": dict(compare(passes[x], passes[y]), **moves(passes[x], passes[y]))
               for i, x in enumerate(names) for y in names[i + 1:]},
    "duree_s": durations,
}, ensure_ascii=False))
detail = os.environ.get("GUARD_DETAIL")
if detail:
    # Classes seules, par rang d'entrée : aucun contenu.
    with open(detail, "w", encoding="utf-8") as h:
        json.dump(passes, h, ensure_ascii=False)
