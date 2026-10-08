"""Micro-banc Ollama : débit d'étiquetage selon OLLAMA_NUM_PARALLEL.

Prompt = gabarit réel d'EmailTaggingService (template.txt) + contenu synthétique varié
(aucune donnée réelle). Concurrence côté client = 50, comme 5 réplicas × ConcurrentMessageLimit 10.
"""
import json, random, statistics, sys, threading, time, urllib.request

PORT, N, CONC, CHARS = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
import os
TPL = open(os.environ.get("TPL", "template.txt"), encoding="utf-8").read()
WORDS = ("patient bilan biologique créatinine potassium sodium hémoglobine plaquettes leucocytes "
         "compte rendu consultation suivi traitement posologie antécédents examen clinique "
         "tension artérielle fréquence cardiaque glycémie cholestérol triglycérides ferritine "
         "échographie radiographie scanner conclusion contrôle à prévoir résultats normaux "
         "valeurs de référence prélèvement laboratoire médecin traitant correspondant").split()

def content(i):
    rnd = random.Random(i)
    out = [f"Compte rendu n°{i}. "]
    while sum(len(w) + 1 for w in out) < CHARS:
        out.append(rnd.choice(WORDS))
        if rnd.random() < 0.08:
            out.append(f"{rnd.uniform(0.5, 200):.1f} mmol/L.")
    return " ".join(out)

def prompt(i):
    return (TPL.replace("{{$documentType}}", random.Random(i).choice(["Biologie", "CompteRendu", "Courrier"]))
               .replace("{{$senderEmail}}", f"labo{i % 37}@exemple.test")
               .replace("{{$content}}", content(i)))

results, lock = [], threading.Lock()
queue = list(range(N))

def worker():
    while True:
        with lock:
            if not queue:
                return
            i = queue.pop()
        body = json.dumps({"model": "qwen2.5:14b", "stream": False,
                           "messages": [{"role": "user", "content": prompt(i)}]}).encode()
        req = urllib.request.Request(f"http://127.0.0.1:{PORT}/api/chat", body,
                                     {"Content-Type": "application/json"})
        t = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=600) as r:
                d = json.loads(r.read())
            ok = True
        except Exception as e:  # noqa: BLE001 — banc
            d, ok = {"error": str(e)}, False
        with lock:
            results.append((ok, time.perf_counter() - t, d))

t0 = time.perf_counter()
threads = [threading.Thread(target=worker) for _ in range(CONC)]
for th in threads: th.start()
for th in threads: th.join()
wall = time.perf_counter() - t0
ok = [r for r in results if r[0]]
lat = sorted(r[1] for r in ok)
pe = [r[2].get("prompt_eval_count", 0) for r in ok]
ec = [r[2].get("eval_count", 0) for r in ok]
pd = [r[2].get("prompt_eval_duration", 0) / 1e9 for r in ok]
ed = [r[2].get("eval_duration", 0) / 1e9 for r in ok]
print(json.dumps({
    "n_ok": len(ok), "n_err": len(results) - len(ok), "wall_s": round(wall, 1),
    "per_min": round(len(ok) / wall * 60, 1),
    "lat_p50_s": round(lat[len(lat) // 2], 1) if lat else None,
    "lat_p95_s": round(lat[int(len(lat) * 0.95) - 1], 1) if lat else None,
    "prompt_tokens_moy": round(statistics.mean(pe)) if pe else None,
    "completion_tokens_moy": round(statistics.mean(ec)) if ec else None,
    "prefill_s_moy": round(statistics.mean(pd), 2) if pd else None,
    "decode_s_moy": round(statistics.mean(ed), 2) if ed else None,
    "json_lisible_pct": round(100 * sum(1 for r in ok if r[2].get("message", {}).get("content", "").strip().startswith(("{", "[", "```"))) / len(ok), 1) if ok else None,
}))
