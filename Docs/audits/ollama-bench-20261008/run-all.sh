#!/usr/bin/env bash
# Pour chaque NUM_PARALLEL : conteneur Ollama de test (port 11435), chauffe, puis 120 requêtes à concurrence 50.
export MSYS_NO_PATHCONV=1
cd "$(dirname "$0")"
for P in ${VALUES:-1 2 4 6}; do
  docker rm -f ollama-bench >/dev/null 2>&1
  docker run -d --gpus=all --name ollama-bench -p 127.0.0.1:11435:11434 -v mss-mail-ollama-models:/root/.ollama \
    -e OLLAMA_NUM_PARALLEL=$P -e OLLAMA_KEEP_ALIVE=24h ollama/ollama:latest >/dev/null
  until curl -s -m 2 http://127.0.0.1:11435/api/version >/dev/null; do sleep 2; done
  TPL=${TPL:-template.txt} python bench.py 11435 3 3 4300 >/dev/null   # chargement du modèle + cache de préfixe
  vram=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | tr -d ' ')
  ps=$(docker exec ollama-bench ollama ps | tail -1 | awk '{print $4, $5, $6}')
  echo "P=$P vram_MiB=$vram ps=[$ps] $(TPL=${TPL:-template.txt} python bench.py 11435 ${N:-120} 50 4300)"
done
docker rm -f ollama-bench >/dev/null 2>&1
