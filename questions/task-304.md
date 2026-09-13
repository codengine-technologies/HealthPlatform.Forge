# questions/task-304.md — outillage visuel absent du poste

**Date** : 2026-09-13
**Étape** : `/develop` (task-304)
**Portée bloquée** : les quatre critères « Outillage visuel et QA » de la DOD.
**Ce qui n'est PAS bloqué** : tout le reste de la US est implémenté, build et
tests verts sur les trois fronts. La chaîne continue.

## Le constat

Le task file demande de modifier `Tools/visual-verify/capture.mjs`,
`Tools/visual-verify/screens.json` et d'y ajouter une fixture `mailboxes.json`.
**Ce répertoire n'existe pas** — ni sur le disque, ni dans l'index git :

```
$ ls Tools/
Blazor-CDA  CDA-Plain-Text.Concole  EmailSender.Console
interop-outil-cda-...  timing
$ git ls-files | grep visual-verify      # (rien)
```

La cause est dans `.gitignore` (lignes 71-87) : `Tools/` est **délibérément
non versionné**, avec une seule exception réintroduite explicitement,
`Tools/timing/` — « `Tools/` is otherwise orphan tooling and stays untracked ;
only the timing harness is forge infrastructure and must survive a fresh
clone ». Le harnais de capture Playwright n'a donc jamais été poussé : il vit
sur le poste qui l'a écrit, et ce poste-ci ne l'a pas.

Les captures de la galerie (`Docs/epics/img/screens/client-mobile/`, dont
`mss-setup.png` et `mss-unconfigured.png`) prouvent qu'il a tourné ; elles sont
versionnées, l'outil qui les produit ne l'est pas.

## Ce que la forge n'a pas fait, et pourquoi

Les quatre critères suivants restent **non satisfaits** :

- [ ] fixture `mailboxes.json` + entrée dans `API_ROUTES` de `capture.mjs`
- [ ] `FAKE_SESSION` / `TOKEN_ONLY_SESSION` refaçonnées sur `currentMailbox`
- [ ] `screens.json` : retrait de `mss-unconfigured` / `mss-setup`, ajout des
      quatre nouveaux écrans
- [ ] galerie : remplacement de `mss-setup.png` et `mss-unconfigured.png`

**Reconstruire le harnais aurait été pire que ne rien faire.** Le task file le
décrit précisément (session factice, `**/api/**` rendant `[]` par défaut,
capture 390×844), mais écrire un `capture.mjs` neuf à partir de cette
description produirait un outil *qui lui ressemble*, pas *celui qui a produit la
galerie existante*. `/verify-visual` exécuterait alors quelque chose d'inventé,
et ses captures ne seraient plus comparables aux précédentes — une régression
silencieuse de la référence visuelle, au moment précis où l'on remplace des
écrans.

## Conséquence immédiate, et elle est réelle

Le task file avertit : le mock `**/api/**` rend `[]` sur tout `GET` non mappé.
Après cette US, `GET /account/mailboxes` rendrait donc `[]` ⇒ **zéro boîte** ⇒
**écran d'onboarding pour TOUTES les captures mobiles**. Dès que le harnais sera
récupéré, la fixture `mailboxes.json` est donc le **premier** geste à faire, avant
toute autre capture — sans quoi la galerie entière devient l'écran d'onboarding.

Les deux PNG `mss-setup.png` et `mss-unconfigured.png` documentent par ailleurs
des écrans **supprimés par cette US** : ils sont périmés dès le merge.

## Ce qu'il faut décider

1. **Récupérer le harnais** depuis le poste qui le porte, puis rejouer
   `/verify-visual task-304` — et, tant qu'à faire, **le versionner** : une
   exception `!Tools/visual-verify/` dans `.gitignore`, au même titre que
   `Tools/timing/`, par le même argument (« must survive a fresh clone »). Un
   outil dont dépend une étape de la chaîne autonome n'est pas de l'outillage
   orphelin.
2. **Ou** acter que la vérification visuelle de cette US se fait à la main au
   HAG, et retirer les quatre critères de la DOD.

La question est pour l'humain : elle porte sur le versionnement d'un outil de la
forge, pas sur le code de la US.
