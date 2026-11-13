<#
.SYNOPSIS
  Empêche la mise en veille du poste tant que la forge tourne (bail renouvelable).

.DESCRIPTION
  Lancé en arrière-plan par Tools/keepawake/keep-awake.sh, jamais à la main.

  Arme SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED) et reste vivant
  tant que le fichier de bail (-LeaseFile) a été touché depuis moins de
  -LeaseSeconds. Chaque étape de la chaîne touche le bail (step.sh, measure.sh) :
  si la forge s'arrête, plante ou attend l'humain, le bail expire et le poste
  retrouve sa veille normale. Aucun réglage système n'est modifié : l'état
  retombe avec le processus, même s'il est tué.

  Dérivé de Api/Mail/tests/loadtest-k6/keep-awake.ps1 (banc de charge), dont il
  garde les deux leçons :
  - Piège UInt32 (2026-08-26) : 0x80000003 est lu comme un Int32 NÉGATIF par
    PowerShell 5.1 et l'appel échoue en silence. La valeur est construite en
    UInt32 explicitement.
  - « Armé » n'est vrai que si l'API rend un état précédent non nul. La ligne
    ARME du journal porte cet état : c'est la preuve d'armement que
    keep-awake.sh attend avant de répondre.
#>
param(
  [Parameter(Mandatory = $true)][string]$LeaseFile,
  [Parameter(Mandatory = $true)][string]$LogFile,
  [Parameter(Mandatory = $true)][string]$PidFile,
  [int]$LeaseSeconds = 10800,
  [int]$PollSeconds = 60,
  [int]$HardCapSeconds = 86400
)

function Log([string]$msg) {
  $line = "{0} {1}" -f (Get-Date -Format 'yyyy-MM-ddTHH:mm:ssK'), $msg
  try { Add-Content -LiteralPath $LogFile -Value $line -Encoding ASCII } catch { }
}

Add-Type -Namespace Forge -Name Power -MemberDefinition @'
[System.Runtime.InteropServices.DllImport("kernel32.dll", SetLastError = true)]
public static extern uint SetThreadExecutionState(uint esFlags);
'@

[uint32]$ES_CONTINUOUS      = [uint32]'2147483648'   # 0x80000000
[uint32]$ES_SYSTEM_REQUIRED = [uint32]'1'            # 0x00000001
[uint32]$flags = $ES_CONTINUOUS -bor $ES_SYSTEM_REQUIRED

$previous = [Forge.Power]::SetThreadExecutionState($flags)
if ($previous -eq 0) {
  Log ("NON ARME pid={0} : SetThreadExecutionState a rendu 0 (GetLastError={1})" -f $PID, [Runtime.InteropServices.Marshal]::GetLastWin32Error())
  exit 1
}
try { Set-Content -LiteralPath $PidFile -Value $PID -Encoding ASCII -NoNewline } catch { }
Log ("ARME pid={0} flags=0x{1:X8} etat_precedent=0x{2:X8} bail={3}s" -f $PID, $flags, $previous, $LeaseSeconds)

$reason = 'bail expire'
try {
  $hardDeadline = (Get-Date).AddSeconds($HardCapSeconds)
  while ($true) {
    Start-Sleep -Seconds $PollSeconds
    if (-not (Test-Path -LiteralPath $LeaseFile)) { $reason = 'bail retire'; break }
    $age = ((Get-Date) - (Get-Item -LiteralPath $LeaseFile).LastWriteTime).TotalSeconds
    if ($age -gt $LeaseSeconds) { $reason = ("bail expire (dernier signe de la forge il y a {0:N0} s)" -f $age); break }
    if ((Get-Date) -gt $hardDeadline) { $reason = 'plafond absolu atteint'; break }
    [void][Forge.Power]::SetThreadExecutionState($flags)   # ré-arme : certains pilotes réinitialisent l'état
  }
} finally {
  [void][Forge.Power]::SetThreadExecutionState($ES_CONTINUOUS)
  try {
    if ((Test-Path -LiteralPath $PidFile) -and ((Get-Content -LiteralPath $PidFile -Raw).Trim() -eq "$PID")) {
      Remove-Item -LiteralPath $PidFile -Force
    }
  } catch { }
  Log ("RELACHE pid={0} : {1}" -f $PID, $reason)
}
