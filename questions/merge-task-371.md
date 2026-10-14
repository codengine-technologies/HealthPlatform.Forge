# merge-task-371 — CI rouge sur `develop` d'api-mail après le merge (non causée par la task)

- **Run** : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/actions/runs/38586719099 (push de db6ffad7, PR #296, catalogue e2e seulement)
- **Échec** : `Restore dependencies` — `NU1902` / `NU1903` en erreur (`TreatWarningsAsErrors`) sur `System.Security.Cryptography.Pkcs` 10.0.0 :
  GHSA-846f-f764-76mx (élevée) et GHSA-2fmv-rv2c-59x7 (modérée). Avis publiés après la CI verte de la PR.
- **Chaîne** : `MailKit 4.17.0 → MimeKit 4.17.0 → System.Security.Cryptography.Pkcs 10.0.0` (transitif, tous les projets).
- **Portée** : toute branche d'api-mail échouera au Restore en CI ; en local, le cache d'audit NuGet ne le voit pas encore (restore vert à 17 h).
- **Remède proposé** : surclasser la dépendance transitive dans `Directory.Packages.props`, comme pour SSH.NET (GHSA-q939-rpr3-3284) et MessagePack — `System.Security.Cryptography.Pkcs` à la version corrigée de l'avis — plus les `packages.lock.json`, dans une PR `chore(deps)` dédiée.
- **Décision humaine** : faire ce correctif maintenant (avant task-370, dont la PR api-mail tomberait aussi au Restore) ?
- client-mobile : CI `develop` verte.
