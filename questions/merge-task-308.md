# questions/merge-task-308.md — CI rouge sur `develop` de `client-mobile` après le merge

> Écrit par `/merge 308 --i-tested` le 2026-09-14. **Les trois PRs sont mergées** — ce
> fichier ne bloque rien, il consigne un échec de CI post-merge (règle 5) et son
> diagnostic.

## Ce qui est rouge

[Run 34896682052](https://github.com/codengine-technologies/HealthPlatform.Mobile/actions/runs/34896682052)
sur `develop` de `client-mobile` — job `build-android`, étape **`Set up Android SDK`**.

```
Warning: Failed to find package 'tools'
Error: The process '/usr/local/lib/android/sdk/cmdline-tools/16.0/bin/sdkmanager'
       failed with exit code 1
```

**Rejoué une fois : même échec.** Ce n'est pas un flaky.

## Ce n'est pas task-308

Trois éléments concordants :

1. **Aucun code n'est compilé à cette étape.** `Set up Android SDK` s'exécute *avant*
   `npm ci`, `cap sync` et le build. Le diff de task-308 sur ce repo est **un seul fichier
   de test** (`src/app/core/auth/mailbox.guard.spec.ts`, 130 lignes).
2. **Le même job est passé sur la PR #71**, 20 minutes plus tôt, sur exactement le même
   contenu — `build-android pass 5m6s`.
3. **`develop` était vert** au run précédent (2026-09-14 17:22, merge de task-304).

La cassure s'est donc produite **entre 17:22 et 21:04**, hors du dépôt.

## La cause

`android-actions/setup-android@v3` installe par défaut le paquet **`tools`** du SDK
Android. Google l'a **retiré de son dépôt** : `sdkmanager` ne le trouve plus et sort en 1.
C'est une cassure externe, qui frappera **tout** dépôt utilisant cette action sans
surcharger son paramètre `packages`.

## Le correctif proposé — une ligne

`.github/workflows/*.yml`, étape ligne 62 :

```yaml
      - uses: android-actions/setup-android@v3
        with:
          packages: ''          # <- ne rien installer ici
```

**Pourquoi c'est sûr** : l'étape suivante du workflow installe déjà explicitement ce dont
le build a besoin —

```yaml
      - name: Install Android SDK packages
        run: |
          sdkmanager --install "platforms;android-36" "build-tools;36.0.0" "platform-tools"
```

`setup-android` n'a donc **aucune raison** d'installer quoi que ce soit : il n'est là que
pour poser `cmdline-tools` et les variables d'environnement. Le paquet `tools` n'était pas
utilisé, il était seulement téléchargé.

## Ce qui n'a pas été fait, et pourquoi

Le correctif **n'a pas été poussé**. C'est une modification de workflow sur un repo
pushable : elle passe par une branche et une PR (règle 5), et son merge appartient à
l'humain (règle 10). Une PR de CI est orthogonale à toute US en cours et peut donc merger
indépendamment (règle 11).

**Action attendue** : valider le correctif ci-dessus, et dire si la forge ouvre la PR.
