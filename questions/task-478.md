# task-478 — Revue anticipée interrompue : relecteur indépendant indisponible (panne d'outillage)

**Étape** : `/review task-478 --code`, étape 5 (revue de code par un relecteur indépendant).

## Blocage

Le sous-agent relecteur échoue avant tout constat. Trois essais, tous sur la même erreur :

```
API Error: 403 Attention Required! | Cloudflare (error type authentication_failed, HTTP 403)
```

- essais 1 et 2 : `claude-opus-5-5` ;
- essai 3 : `claude-sonnet-5-5`.

Ce n'est ni un constat de revue ni un défaut du code : l'API refuse l'authentification des sous-agents. La règle impose
un relecteur **indépendant**. La forge ne remplace pas cette relecture par une auto-relecture de l'auteur.

## État au moment de l'arrêt

- **api-mcp** : branche `feat/task-478-mcp-messagerie-connexion-e-cps-et`, poussée, à jour avec origin.
  - Commits : `0397b4a` (feature), `f8ec587` (dossier `Tools` versionné), `a2f459a` (passe qualité).
  - Build 0 erreur, tests 74/74, vert marqué (`Tools/green/green.py`) sur `a2f459a`.
- **Règle 1b** : 21 preuves rouges par mutation (M01 à M21), toutes rouges. La table est dans le `## Develop log` et le
  `## Code Review Summary` du task file.
- **Task** : reste en `wip-*`. Aucune PR ouverte.
- **Plan de contrôle** : commité localement, **pas poussé**. Il contient l'enregistrement d'api-mcp dans `CLAUDE.md`
  et les playbooks : c'est un changement de chaîne, à relire avant le push (règle d'or 7).

## Décision attendue

Une fois l'API de nouveau joignable, relancer `/review task-478 --code`. La chaîne reprend alors seule :
- `/sonar` skip (api-mail non touché) ;
- lint skip ;
- `/e2e` skip (aucune voie) ;
- `/review` (validation finale, PR) ;
- `/tech-writer E026`.
