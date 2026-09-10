# todo-task-297.md — Le cache Redis stocke des corps de message de 1,5 Mo et sature seul : borner ce que l'on met en cache pour que le cache réponde

**Repos**: api-mail
**Dependencies**: —
**Epic**: E015
**Single frontend**: true
**Priorité**: **2** — le cache applicatif expire (500 ms) des milliers de fois par tir
**sans aucune autre charge Redis**, et il entraîne le spill du journal d'audit dans sa
saturation (contre-pression prématurée). Il ne fait pas perdre de donnée : il fait attendre
le médecin et fragilise un mécanisme de conformité.

> **Origine** : campagne task-292 du 2026-09-09, finding **F-292-3**, tranché par le tir A/B
> « journal désactivé » (`Docs/audits/api-mail-loadtest-journey-1000-task292-audit-off-20260909.md`).
> Le finding avait d'abord été attribué au spill d'audit (task-186/292) ; la mesure l'exonère.

## Objective

Que le cache Redis d'api-mail **reste disponible** à 1000 médecins : aucune entrée qui bloque
l'instance pendant des millisecondes, un taux de timeouts du cache proche de zéro, et un spill
d'audit qui ne subit plus la saturation du cache.

### Ce qui a été mesuré (2026-09-09, journey 1000, journal d'audit DÉSACTIVÉ)

| Grandeur | Valeur |
|---|---|
| `[Cache] ⏱️ Timeout getting key` (Warning, `ResilientCacheService`, budget 500 ms) | **6 568** sur le tir sans journal ; 21 835 / 8 778 / 10 773 sur les trois tirs avec journal |
| `[Cache] Best-effort Set failed` | 25 (287 avec journal) |
| CPU Redis (`mss-mail-redis`, mono-thread) | 0,21 cœur en moyenne, **1,15 cœur en pointe** en régime, à trois reprises de plus de 10 min |
| Slowlog Redis (ce qui bloque l'instance) | `HMSET mail:email:<adresse>:INBOX:<uid>` avec un champ `data` de **160 Ko à 1,47 Mo** (corps de message complet, JSON) en 11 à 16 ms ; `HMSET usersettings:*` ; quelques `SET mss:audit:purge:*` |
| Débit Redis | ~500 à 640 ops/s, 3,5 Mo/s en sortie |
| Mémoire Redis | 2,0 à 2,8 Go, `db0` ~14 500 clés |
| Effet croisé | avec le journal actif, 38 attentes / 18 refus de contre-pression d'audit sur `Spill buffer unreachable` alors que la borne du spill n'était qu'à 70 000 sur 120 000 : Redis ne répondait pas dans les temps |

**Mécanique établie.** Redis exécute une commande à la fois. Une entrée `mail:email:*` de 1,5 Mo
(le corps texte + HTML complet d'un message, sérialisé) coûte 15 ms à écrire et autant à lire ;
quelques-unes par seconde suffisent à faire dépasser 500 ms aux lectures de petites clés en file
derrière (`user:id:*`, `usersettings:*`, résumés). Le cache écrit ensuite le message en lecture à
la première demande (`MailController.GetEmail`, clé `RedisKeys.Mail.Email`) et l'invalidateur le
retire à chaque changement de statut : c'est un cache **chaud et volumineux** sur une instance
partagée avec le spill d'audit, les marqueurs de purge et le cache d'identité.

### Contenu attendu

1. **Borner ce qui entre en cache.** Pour la clé `mail:email:*` : ne pas mettre en cache une entrée
   dont la charge sérialisée dépasse un seuil (ordre de grandeur **64 à 128 Ko**, à fixer par la
   distribution mesurée des tailles) — la lecture retombe alors sur la base (`MailContents`), qui
   est le chemin normal depuis task-273 ; ou mettre en cache le message **sans** ses corps
   (`Body`, `BodyHtml`) et ne garder que les en-têtes/PJ/résumé si c'est ce que le chemin de
   lecture consomme en premier. Le choix revient à `/develop`, sous contrainte : **aucune
   régression fonctionnelle** de l'affichage d'un message.
2. **Compresser ou non** : si le corps reste en cache, le compresser (gzip/brotli côté service de
   cache) est une option à chiffrer ; l'objectif reste la borne de taille, pas le tassement.
3. **Mesurer la distribution des tailles** d'entrées `mail:email:*` (histogramme en Ko, p50/p95/max)
   et le nombre d'entrées refusées par la borne : compteurs exposés au collecteur
   (`mss_cache_entry_bytes`, `mss_cache_oversize_skipped_total`), au moins un test de capture.
4. **Ne pas toucher au budget de 500 ms** de `ResilientCacheService` (Sdk) : il est le symptôme, pas la cause.
5. **Re-mesurer au banc** : tir journey 1000 iso (mêmes bases), attendu : `Timeout getting key` ÷ 10
   au moins, Redis sous 0,5 cœur en pointe, plus aucun `Spill buffer unreachable` du journal d'audit
   à charge égale, et latence de l'étape « Ouvrir un message enrichi » inchangée ou meilleure.

### Hors périmètre (explicite)

- Une instance Redis dédiée au journal d'audit (task-292 a retenu une base logique distincte, `db1`) —
  non nécessaire si le cache cesse de bloquer l'instance ; à rouvrir si la mesure le contredit.
- Le cache des résumés (`mail:summary:*`) et des dossiers : petits, hors slowlog.
- Le dimensionnement de Redis (mémoire, threads I/O) : levier infra, à n'envisager qu'après la borne applicative.

## Definition of Done

- [ ] Build passes on api-mail (0 errors)
- [ ] Tests pass (0 failures)
- [ ] Test unitaire : une entrée `mail:email:*` au-dessus du seuil n'est **pas** écrite en cache et le
      compteur `oversize_skipped` s'incrémente ; une entrée sous le seuil l'est
- [ ] Test unitaire : la lecture d'un message dont l'entrée a été refusée par la borne rend le **même
      contenu** que par le cache (repli base), y compris corps HTML et pièces jointes
- [ ] Test de capture de métriques : histogramme des tailles + compteur exposés (classe sérialisée, task-291)
- [ ] Seuil configurable (`Cache:MaxEntryBytes` ou équivalent), défaut justifié par la distribution mesurée
      et documenté dans `appsettings.json`
- [ ] Aucune donnée de santé dans les logs du nouveau chemin (taille et clé seulement — la clé contient
      l'adresse MSSanté du praticien, pas de donnée patient ; ne jamais journaliser le contenu)
- [ ] Mesure au banc consignée dans le task file : tir journey 1000 iso avant/après — `Timeout getting
      key`, CPU Redis pointe, slowlog (aucune commande > 5 ms sur `mail:email:*`), `Spill buffer
      unreachable` = 0 avec journal actif, p50/p95 de l'étape 3 inchangés ou meilleurs

## Manual Test Plan

- **Fonctionnel (dev)** : `cd Api/Mail && dotnet run --project src/AppHost` ; ouvrir un message lourd
  (corps HTML long, plusieurs PJ) dans le client Blazor ; vérifier l'affichage complet ; relire le
  même message (servi par la base) ; contrôler dans Redis (`redis-cli --bigkeys`, `MEMORY USAGE
  mail:email:…`) qu'aucune entrée `mail:email:*` ne dépasse le seuil et que le compteur
  `mss_cache_oversize_skipped_total` a bougé.
- **Banc** (skill `loadtest-skill`, mode distant, bases gardées) : tir journey 1000 r2 iso au tir
  `report-journey-1000-task292-audit-off-20260909-173951.md` (référence « sans journal ») **et** au
  tir `fix2` (référence « avec journal »). Pendant le régime : `redis-cli slowlog get 20` (aucun
  `HMSET mail:email:*` > 5 ms), `docker stats` Redis (< 0,5 cœur), Seq
  `select count(*) from stream where @MessageTemplate like '%Timeout getting key%'` sur la fenêtre.
- **Ce que l'humain doit voir** : timeouts du cache ÷ 10 au moins, 0 `Spill buffer unreachable`,
  étape 3 « Ouvrir un message enrichi » au moins aussi rapide, aucun message tronqué ou vide.
- **Données de test** : boîtes `loadtest-*`, `JEUX_TESTS_FULL`. Aucune donnée de santé réelle.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors exigence DSR directe — robustesse d'un composant technique
- **Exigences DSR honorées** : non applicable
- **INS** : non applicable — le cache porte des messages MSSanté, jamais d'INS en clé ; le contenu
  (qui peut contenir des données de santé) est déjà en cache aujourd'hui ; cette US en **réduit**
  l'emprise (moins de corps de message dans Redis)
- **Authentification PS** : inchangée
- **Habilitations** : inchangées — le cache est scopé par adresse du praticien (clé)
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : effet indirect positif — le spill du journal d'audit (task-292) cesse d'être
  victime de la saturation du cache ; aucun événement nouveau à journaliser
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — Redis est dans le périmètre HDS de Staging/Production ; réduire les
  corps de message en cache réduit la surface de données de santé en mémoire partagée
- **AIPD / impact RGPD** : inchangée — aucun traitement nouveau ; la note de l'AIPD sur les données
  transitant par Redis peut mentionner la borne comme mesure de minimisation
