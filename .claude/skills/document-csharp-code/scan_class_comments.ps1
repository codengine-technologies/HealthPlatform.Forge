$root = "D:\TechWatch\HealthPlatform\Api\Mail"
$docsDir = Join-Path $root "docs"
if (-not (Test-Path $docsDir)) {
    New-Item -ItemType Directory -Path $docsDir | Out-Null
}

$files = Get-ChildItem -Path $root -Recurse -Filter "*.cs" | Where-Object {
    $_.FullName -notmatch "\\(obj|bin)\\"
}

$results = @()

foreach ($f in $files) {
    $lines = Get-Content $f.FullName
    $missing = $false
    $className = ""

    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i] -match '^\s*(public|internal|sealed|abstract|static|partial|private|protected)\s+.*\bclass\b\s+(\w+)') {
            $className = $Matches[2]
            $hasComment = $false

            for ($j = $i - 1; $j -ge 0; $j--) {
                $trim = $lines[$j].Trim()
                if ($trim -eq "") { continue }
                # Skip attributes [ApiController], [Route(...)], etc.
                if ($trim -match '^\[') { continue }
                if ($trim -match '^///\s*<') { $hasComment = $true; break }
                if ($trim -match '^///') { $hasComment = $true; break }
                if ($trim -match '^/\*\*?') { $hasComment = $true; break }
                if ($trim -match '^\*') { $hasComment = $true; break }
                if ($trim -match '^//') { $hasComment = $true; break }
                break
            }

            if (-not $hasComment) {
                $missing = $true
                break
            }
        }
    }

    if ($missing) {
        $relative = $f.FullName.Substring($root.Length + 1)
        $results += [PSCustomObject]@{
            File = $relative
            Class = $className
        }
    }
}

$output = @()
$output += "Classes sans commentaire d'entete"
$output += "Date: $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
$output += "Total: $($results.Count) fichier(s)"
$output += ""
$output += "Fichier`tClasse"

foreach ($r in ($results | Sort-Object File)) {
    $output += "$($r.File)`t$($r.Class)"
}

$outputPath = Join-Path $docsDir "classes-without-comments.txt"
$output -join "`r`n" | Set-Content $outputPath -Encoding UTF8

$csvPath = Join-Path $docsDir "classes-without-comments.csv"
$results | Sort-Object File | Export-Csv -Path $csvPath -NoTypeInformation -Encoding UTF8

Write-Host "Done. $($results.Count) files without class header comments."
Write-Host "Output: $outputPath"
Write-Host "CSV: $csvPath"
