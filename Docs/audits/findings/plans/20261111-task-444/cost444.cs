#:project D:/TechWatch/HealthPlatform/Api/Mail/src/Infrastructure/mss.mail.infrastructure.csproj
#:property TreatWarningsAsErrors=false
#:property Nullable=enable
#:property PublishAot=false

// task-444 — coût de l'enrichissement de la réponse (textes de la page + extraits + patients trouvés), mesuré sur
// la copie srch_lab de la boîte de formation. Une page de 50 résultats, 30 passages par requête après 3 de chauffe.
using System.Diagnostics;
using HealthPlatform.Dtos.Mss;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging.Abstractions;
using mss.mail.application.Helpers;
using mss.mail.application.Models;
using mss.mail.Infrastructure.Persistance;
using mss.mail.Infrastructure.Repositories.MailDb;
using Pgvector.EntityFrameworkCore;

var options = new DbContextOptionsBuilder<MailDataContext>()
    .UseNpgsql(Environment.GetEnvironmentVariable("PG444")!, o => o.UseVector())
    .Options;
await using var db = new MailDataContext(options);
var repository = new SemanticSearchRepository(db, NullLogger<SemanticSearchRepository>.Instance);

string[] queries = ["hemoglobine", "urgent", "cholesterol", "catherine bernard", "bilan lipidique cholesterol total", "compte rendu synthese"];
var all = new List<double>();
foreach (var query in queries)
{
    var terms = SearchTerms.Parse(query).Terms;
    var patterns = terms.Select(t => $"%{t}%").ToArray();
    // The page : the 50 most recent INBOX mails holding a word (untimed, as the keyword engine would rank them).
    var uids = await db.Database.SqlQueryRaw<int>("""
        SELECT m."Uid" AS "Value" FROM "Mails" m WHERE m."FolderPath" = 'INBOX' AND (
            public.search_normalize(coalesce(m."Subject", '')) LIKE ANY({0})
            OR EXISTS (SELECT 1 FROM "MailContents" c WHERE c."MailId" = m."Id" AND public.search_normalize(c."Body") LIKE ANY({0}))
            OR EXISTS (SELECT 1 FROM "MailMedicalDocuments" d WHERE d."MailId" = m."Id" AND public.search_normalize(d."Body") LIKE ANY({0})))
        ORDER BY m."SentDate" DESC NULLS LAST LIMIT 50
        """, new object[] { patterns }).ToListAsync();
    var designation = PatientQuery.Parse(query);
    var times = new List<double>();
    var located = 0;
    for (var pass = 0; pass < 33; pass++)
    {
        var page = uids.Select(u => new SemanticSearchResult { Uid = (uint)u, FolderPath = "INBOX", MatchGroup = SearchMatchGroup.AllTerms }).ToList();
        var watch = Stopwatch.StartNew();
        if (!designation.IsEmpty)
        {
            var candidates = await repository.FindPatientCandidatesAsync(designation.LastNameKeys, designation.Ins, SearchLimits.PatientCandidatesMax);
            _ = candidates.Count(c => designation.Matches(c.LastName, c.FirstName, c.Birthday));
        }

        var texts = await repository.GetMailTextsAsync([.. page.Select(r => r.Uid)], ["INBOX"]);
        var byKey = texts.ToDictionary(t => t.Uid);
        foreach (var result in page)
        {
            if (byKey.TryGetValue(result.Uid, out var text))
            {
                SearchHitEnrichment.Apply(result, text, terms);
            }
        }

        watch.Stop();
        if (pass >= 3)
        {
            times.Add(watch.Elapsed.TotalMilliseconds);
            located = page.Count(r => r.Excerpt is not null);
        }
    }

    times.Sort();
    all.AddRange(times);
    Console.WriteLine($"{query,-38} page={uids.Count,2} extraits={located,2} p50={times[times.Count / 2],7:F1} ms  p95={times[(int)(times.Count * 0.95)],7:F1} ms  max={times[^1],7:F1} ms");
}

all.Sort();
Console.WriteLine($"{"TOUTES",-38} n={all.Count} p50={all[all.Count / 2]:F1} ms  p95={all[(int)(all.Count * 0.95)]:F1} ms");
