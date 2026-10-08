# Micro-banc Ollama — débit d'étiquetage (2026-10-08)

Mesure le débit d'étiquetage de `qwen2.5:14b` selon `OLLAMA_NUM_PARALLEL`, avec le gabarit réel
d'`EmailTaggingService` et un contenu synthétique (aucune donnée réelle). La concurrence côté client
vaut 50, soit 5 réplicas × `ConcurrentMessageLimit` 10. Source de task-355.

- `template.txt` : gabarit d'origine (bloc « Contexte » avant la grille), extrait du code au 2026-10-08.
- `template-prefix.txt` : même gabarit, bloc « Contexte » déplacé juste avant « Contenu du document ».
- `bench.py PORT N CONC CHARS` : `CHARS=4300` donne ~2 548 tokens de prompt, l'ordre de grandeur réel
  (≈ 2 550 mesurés au banc).
- `run-all.sh` : pour chaque valeur de `VALUES` (défaut `1 2 4 6`), conteneur `ollama-bench` sur le
  port 11435 avec le volume `mss-mail-ollama-models`, chauffe, puis 120 requêtes. Variable `TPL` pour
  choisir le gabarit. **Arrêter d'abord `mss-mail-ollama`** : deux modèles chargés ne tiennent pas en
  16 Go de VRAM.

Pour mesurer le gabarit livré, régénérer `template.txt` depuis `TaggingPromptTemplate` et
`TaggingRubric`, littéraux bruts désindentés, puis lancer `VALUES="4" ./run-all.sh`.

| Gabarit | P | /min | attente p50 | prefill moy. | VRAM |
|---|---|---|---|---|---|
| origine | 1 | 40,8 | 68,9 s | 0,71 s | 11,2 Go |
| origine | 2 | 45,6 | 63,1 s | 0,81 s | 12,2 Go |
| origine | 4 | 45,6 | 63,3 s | 1,02 s | 13,6 Go |
| origine | 6 | 49,2 | 56,1 s | 1,24 s | 15,2 Go |
| Contexte après la grille | 1 | 51,7 | 55,0 s | 0,37 s | 11,3 Go |
| Contexte après la grille | 2 | 65,3 | 41,3 s | 0,44 s | 12,2 Go |
| Contexte après la grille | 4 | **76,4** | 35,9 s | 0,52 s | 13,6 Go |
