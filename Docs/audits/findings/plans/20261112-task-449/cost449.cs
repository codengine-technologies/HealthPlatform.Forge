#:project D:/TechWatch/HealthPlatform/Api/Mail/src/Infrastructure/mss.mail.infrastructure.csproj
#:property TreatWarningsAsErrors=false
#:property Nullable=enable
#:property PublishAot=false

// task-449 — coût des suggestions de la barre de recherche, et de la recherche exacte entre guillemets comparée à la
// recherche plein texte habituelle, mesurés sur la copie srch_lab de la boîte de formation. 30 passages par requête
// après 3 de chauffe, index de recherche construits.
using System.Diagnostics;
using HealthPlatform.Dtos.Mss;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging.Abstractions;
using Microsoft.SemanticKernel;
using mss.mail.application.Helpers;
using mss.mail.application.Models;
using mss.mail.application.Services.Implementation;
using mss.mail.Infrastructure.Persistance;
using mss.mail.Infrastructure.Repositories.MailDb;
using Pgvector.EntityFrameworkCore;

var options = new DbContextOptionsBuilder<MailDataContext>()
    .UseNpgsql(Environment.GetEnvironmentVariable("PG449")!, o => o.UseVector())
    .Options;
await using var db = new MailDataContext(options);
var repository = new SemanticSearchRepository(db, NullLogger<SemanticSearchRepository>.Instance);
var search = new SemanticSearchService(Kernel.CreateBuilder().Build(), repository, NullLogger<SemanticSearchService>.Instance);

// Les index de recherche, comme en production après la première recherche de la boîte.
await repository.FindFullTextMatchesAsync(["bilan"], SearchContentType.Both, "INBOX");
for (var i = 0; i < 600; i++)
{
    var ready = await db.Database.SqlQueryRaw<int>("""
        SELECT count(*)::int AS "Value" FROM pg_index i JOIN pg_class c ON c.oid = i.indexrelid
        WHERE c.relname LIKE 'IX_%_SearchText' AND i.indisvalid AND i.indisready
        """).SingleAsync();
    if (ready == 4) break;
    await Task.Delay(1000);
}

static (double P50, double P95) Percentiles(List<double> times)
{
    times.Sort();
    return (times[times.Count / 2], times[(int)(times.Count * 0.95)]);
}

async Task<List<double>> TimeAsync(Func<Task> run)
{
    var times = new List<double>();
    for (var pass = 0; pass < 33; pass++)
    {
        var watch = Stopwatch.StartNew();
        await run();
        watch.Stop();
        if (pass >= 3) times.Add(watch.Elapsed.TotalMilliseconds);
    }

    return times;
}

Console.WriteLine("== Suggestions (patients + expéditeurs + destinataires + types), ce que fait SearchSuggestionService");
string[] typed = ["be", "ber", "bern", "cath", "ma", "mar", "lab", "cerb", "dupo", "hosp"];
var allSuggestions = new List<double>();
foreach (var text in typed)
{
    var words = System.Text.RegularExpressions.Regex.Matches(SearchTerms.Normalize(text), @"[\p{L}\p{N}]+").Select(m => m.Value).ToList();
    var counts = (0, 0, 0);
    var times = await TimeAsync(async () =>
    {
        var patients = await repository.SuggestPatientsAsync(words, 5);
        var senders = await repository.SuggestCorrespondentsAsync(words, SearchCorrespondentRole.Sender, null, 5);
        var recipients = senders.Count >= 5 ? [] : await repository.SuggestCorrespondentsAsync(words, SearchCorrespondentRole.Recipient, null, 5);
        _ = MedicalDocumentTypeCatalog.Matching(words, 5);
        counts = (patients.Count, senders.Count, recipients.Count);
    });
    allSuggestions.AddRange(times);
    var (p50, p95) = Percentiles(times);
    Console.WriteLine($"{text,-8} patients={counts.Item1} exp={counts.Item2} dest={counts.Item3}  p50={p50,6:F1} ms  p95={p95,6:F1} ms  max={times[^1],6:F1} ms");
}

var (sp50, sp95) = Percentiles(allSuggestions);
Console.WriteLine($"{"TOUTES",-8} n={allSuggestions.Count} p50={sp50:F1} ms  p95={sp95:F1} ms");

Console.WriteLine();
Console.WriteLine("== Recherche exacte entre guillemets / plein texte habituel (même texte), page de 50, INBOX");
string[] phrases = ["compte rendu", "bilan biologique", "cher confrère", "bien confraternellement", "résultats d'analyses"];
var exactAll = new List<double>();
var plainAll = new List<double>();
foreach (var phrase in phrases)
{
    var exactCount = 0;
    var plainCount = 0;
    var exact = await TimeAsync(async () => exactCount = (await search.SearchAsync(Options($"\"{phrase}\""))).Count);
    var plain = await TimeAsync(async () => plainCount = (await search.SearchAsync(Options(phrase))).Count);
    exactAll.AddRange(exact);
    plainAll.AddRange(plain);
    var (e50, e95) = Percentiles(exact);
    var (p50, p95) = Percentiles(plain);
    Console.WriteLine($"{phrase,-26} exacte: {exactCount,2} rés. p50={e50,6:F1} p95={e95,6:F1} ms | habituelle: {plainCount,2} rés. p50={p50,6:F1} p95={p95,6:F1} ms");
}

var (ea50, ea95) = Percentiles(exactAll);
var (pa50, pa95) = Percentiles(plainAll);
Console.WriteLine($"{"TOUTES",-26} exacte p50={ea50:F1} p95={ea95:F1} ms | habituelle p50={pa50:F1} p95={pa95:F1} ms");

static SemanticSearchOptions Options(string query) => new()
{
    Query = query,
    MaxResults = 50,
    FolderPath = "INBOX",
    SearchMode = SearchMode.FullTextOnly,
    SearchType = SearchContentType.Both,
};
