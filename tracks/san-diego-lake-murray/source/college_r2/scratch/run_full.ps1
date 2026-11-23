# Lake Murray's chain BY HAND on a scratch workshop, from the author phase to the gate's own ground check on the exported
# road kn5. The commands are tools/ship_track.sh's own, in its order; that file is the authority, this one a copy to keep
# in step with it. Nothing is installed, nothing outside the workshop is written but the logs.
#
#   python make_ws.py <airoso> san-diego-lake-murray <new empty workshop>          (seeds it as the chain's sync-in does)
#   powershell -File run_full.ps1 -Ws <workshop> -Eng <an engine-july copy> [-From <step>] [-To <step>] [-Log <dir>]
#   powershell -File run_gates.ps1 -Ws <workshop> -Eng <the same>                  (street + Speedway gates, afterwards)
#   python ground_look.py <airoso> <workshop>                                      (the places behind the check's numbers)
#
# One Blender at a time, each at below-normal priority (the PC may be building). Why this exists: Lake Murray 0.20.5's
# first rehearsal (2026-11-23) stopped at kn5_ground_check on ground the College step had made; the scratch pass before it
# had run the prep and nothing after it. Every College change goes through this run before it is pushed.
param([Parameter(Mandatory = $true)][string]$Ws, [Parameter(Mandatory = $true)][string]$Eng, [string]$From = "college_data", [string]$To = "",
      [string]$Air = "", [string]$Log = "", [string]$Blender = "C:\Program Files\Blender Foundation\Blender 4.2\blender.exe")
if (-not $Air) { $Air = (Resolve-Path "$PSScriptRoot\..\..\..\..\..").Path }
if (-not $Log) { $Log = "$Ws\_scratch_log" }
$r2 = "$Air\tracks\san-diego-lake-murray\source\college_r2"
$slug = "san_diego_lake_murray"
$pb = "$Ws\blender\$slug.blend"
New-Item -ItemType Directory -Force $Log | Out-Null
$order = @("college_data", "college_split", "college_middle", "college_ground", "median_rebuild", "median_tops", "lamp_heads", "walk_grade", "race_bands",
           "race_planned_gate", "layout_dummies", "race_author", "signs", "race_verify",
           "prep", "thin", "freeway", "rock", "red", "walk_seat", "road_wear", "split", "export_road", "ground_check", "road_wear_check")
$start = [array]::IndexOf($order, $From)
$stop = if ($To) { [array]::IndexOf($order, $To) } else { $order.Count - 1 }
if ($start -lt 0 -or $stop -lt 0) { "no such step; the steps: $($order -join ', ')"; exit 2 }
function Want($tag) { $i = [array]::IndexOf($order, $tag); return ($i -ge $start -and $i -le $stop) }
function Run-Low($exe, $argList, $tag, $cwd) {
  $t0 = Get-Date
  $p = Start-Process -FilePath $exe -ArgumentList $argList -PassThru -NoNewWindow -RedirectStandardOutput "$Log\$tag.out.txt" -RedirectStandardError "$Log\$tag.err.txt" -WorkingDirectory $cwd
  $h = $p.Handle
  $p.PriorityClass = "BelowNormal"
  $p.WaitForExit()
  "== $tag : exit $($p.ExitCode) in $([int]((Get-Date) - $t0).TotalSeconds) s"
  return $p.ExitCode
}
function Step($tag, $exe, $argList, $pattern, $width, $cwd) {
  if (-not (Want $tag)) { return }
  $rc = Run-Low $exe $argList $tag $cwd
  $rc[0]
  Get-Content "$Log\$tag.out.txt" | Select-String $pattern | ForEach-Object { $_.Line.Substring(0, [Math]::Min($width, $_.Line.Length)) }
  if ($rc[-1] -ne 0) { "STOP at $tag"; Get-Content "$Log\$tag.err.txt" -Tail 12; Get-Content "$Log\$tag.out.txt" -Tail 6; exit 1 }
}
$q = '"'
# ---------------------------------------------------------------------------------------------------------- author
Step "college_data" "python" @("$r2\college_split_data.py", $Ws, "--chain") "^\[" 300 $Air
foreach ($s in @("split", "middle", "ground")) {
  Step "college_$s" $Blender @("--background", "$Ws\loop.blend", "--python-exit-code", "1", "--python", "$r2\college_${s}_blend.py") "^\[college_$s\]|FATAL|Error|Traceback" 3000 $Ws
}
Step "median_rebuild" $Blender @("--background", "--python-exit-code", "1", "--python", "$Air\tools\author_median_rebuild_blend.py", "--", $Ws, "--v021", "$Air\tracks\san-diego-lake-murray\scripts-v021") "^\[median-rebuild\]|FATAL|Error|Traceback" 700 $Ws
Step "median_tops" $Blender @("--background", "--python-exit-code", "1", "--python", "$Air\tools\author_median_tops_blend.py", "--", $Ws) "^\[median-tops\]|FATAL|Error|Traceback" 500 $Ws
Step "lamp_heads" $Blender @("--background", "--python-exit-code", "1", "--python", "$Air\tools\author_lamp_heads_blend.py", "--", $Ws) "^\[heads\]|FATAL|Error|Traceback" 400 $Ws
Step "walk_grade" $Blender @("--background", "--python-exit-code", "1", "--python", "$Air\tools\author_walk_grade_blend.py", "--", $Ws) "^\[walk-grade\]|FATAL|Error|Traceback" 500 $Ws
if (Want "race_bands") {
  Remove-Item "$Ws\data\no_route.*.planned.json", "$Ws\data\no_route.race_cw.json", "$Ws\data\no_route.race_acw.json", "$Ws\data\no_route.north_cw.json", "$Ws\data\no_route.north_acw.json" -ErrorAction SilentlyContinue
}
Step "race_bands" "python" @("tools/barrier_bands.py", $Ws) "^\[bands\] \S+( lap \S+)?: |planned no_route|FAIL|Error|Traceback" 200 $Air
Step "race_planned_gate" "python" @("$PSScriptRoot\planned_gate.py", "$Ws\data", "race_cw", "race_acw", "north_cw", "north_acw") "planned|PLANNED" 200 $Air
Step "layout_dummies" "python" @("tools/layout_dummies.py", $Ws) "wrote" 200 $Air
Step "race_author" $Blender @("--background", "--python-exit-code", "1", "--python", "$Air\tools\author_race_furniture_blend.py", "--", $Ws) "^\[race\].*(COMMON|closure \()|Error|Traceback" 200 $Ws
if (Want "signs") {
  $rc = Run-Low $Blender @("--background", "--python-exit-code", "1", "--python", "$Air\tools\author_signs_blend.py", "--", $Ws) "signs" $Ws
  $rc[0]; Get-Content "$Log\signs.out.txt" | Select-String "^\[signs\] \d+ placed|Error|Traceback" | ForEach-Object { $_.Line.Substring(0, [Math]::Min(300, $_.Line.Length)) }
  if ($rc[-1] -ne 0) { "STOP at signs"; Get-Content "$Log\signs.err.txt" -Tail 12; exit 1 }
  $rc = Run-Low "python" @("tools/verify_signs.py", $Ws, "--blend", "$Ws\loop.blend", "--blender", "$q$Blender$q") "signs_verify" $Air
  $rc[0]; Get-Content "$Log\signs_verify.out.txt" | Select-String "FAIL|PASS" | ForEach-Object { $_.Line.Substring(0, [Math]::Min(300, $_.Line.Length)) }
  if ($rc[-1] -ne 0) { "STOP at signs_verify"; Get-Content "$Log\signs_verify.err.txt" -Tail 12; exit 1 }
}
if (Want "race_verify") {
  foreach ($lap in @("", "college", "north")) {
    $a = @("tools/verify_race.py", $Ws); $tag = "race_verify"
    if ($lap) { $a += @("--lap", $lap); $tag = "race_verify_$lap" }
    $rc = Run-Low "python" $a $tag $Air
    $rc[0]; Get-Content "$Log\$tag.out.txt" | Select-String "G scenery|FAIL|OK ->|FAILED" | ForEach-Object { $_.Line.Substring(0, [Math]::Min(300, $_.Line.Length)) }
    if ($rc[-1] -ne 0) { "STOP at $tag"; Get-Content "$Log\$tag.err.txt" -Tail 12; exit 1 }
  }
}
# ------------------------------------------------------- prep and its sub-steps (tools/ship_track.sh prep_prep)
Step "prep" $Blender @("--background", "--python-exit-code", "1", "--python", "$Eng\scripts\ac\build_kn5_loop.py", "--", $Ws) "terrain conform|kept-cell|house seat|terrain tiles|FATAL|Error|Traceback" 330 $Ws
if (Test-Path "$Ws\data\terrain.tiers.json.gz") {
  Step "thin" $Blender @("--background", "--python-exit-code", "1", "--python", "$Air\tools\thin_terrain_blend.py", "--", $pb, "--project", $Ws) "^\[thin\] terrain|Error|Traceback" 330 $Ws
}
if (Want "freeway") {
  $rc = Run-Low "python" @("tools/freeway_i8.py", $Ws) "freeway" $Air
  $rc[0]; Get-Content "$Log\freeway.out.txt" | Select-Object -Last 2
  if ($rc[-1] -ne 0) { "STOP at freeway"; Get-Content "$Log\freeway.err.txt" -Tail 12; exit 1 }
  if (Test-Path "$Ws\data\freeway_i8.json") { "data/freeway_i8.json exists: tools/author_freeway_blend.py is NOT in this runner; add it before trusting the run"; exit 1 }
}
if (Want "rock") { Remove-Item "$Ws\data\rock_faces.json" -ErrorAction SilentlyContinue }
Step "rock" $Blender @("--background", "--python-exit-code", "1", "--python", "$Air\tools\rock_faces_blend.py", "--", $pb, "--project", $Ws) "^\[rock\]|Error|Traceback" 330 $Ws
if (Test-Path "$Ws\data\red_repairs.plan.json") {
  Step "red" $Blender @("--background", "--python-exit-code", "1", "--python", "$Air\tools\red_repairs_blend.py", "--", $pb, "--project", $Ws) "^\[red\]|Error|Traceback" 330 $Ws
}
Step "walk_seat" $Blender @("--background", "--python-exit-code", "1", "--python", "$Air\tools\author_walk_grade_blend.py", "--", $pb, "--project", $Ws, "--seat") "^\[walk-grade\] --seat:|FATAL|Error|Traceback" 330 $Ws
# the road-wear bake, last in prep (tools/ship_track.sh prep_prep; opt-in on the config's road_wear key). Its time is printed:
# the step line's seconds are the bake's
if ((Want "road_wear") -and ((Get-Content "$Ws\track.config.json" -Raw | ConvertFrom-Json).road_wear)) {
  Remove-Item "$Ws\data\road_wear.json" -ErrorAction SilentlyContinue
  Step "road_wear" $Blender @("--background", "--python-exit-code", "1", "--python", "$Air\tools\road_wear_blend.py", "--", $pb, "--project", $Ws, "--eng", $Eng) "^\[road_wear\]|^\[road_lanes\] \d|FATAL|Error|Traceback" 400 $Ws
}
# ------------------------------------------------------------------------------------ split, road kn5, ground check
Step "split" $Blender @("--background", "--python-exit-code", "1", "--python", "$Air\tools\split_exports_blend.py", "--", $pb, "--project", $Ws, "--out-dir", "$Ws\blender\split") "^\[split\] main|Error|Traceback" 260 $Ws
Step "export_road" $Blender @("--background", "--python-exit-code", "1", "--python", "$Eng\scripts\ac\export_kn5_addon.py", "--", $Ws, "--blend", "$Ws\blender\split\loop_main.blend") "KN5 EXISTS|Error|Traceback" 260 $Ws
if (Want "ground_check") {
  $rc = Run-Low "python" @("-m", "scripts.ac.kn5_ground_check", $Ws, "--json", "$Ws\data\kn5_ground_check.scratch.json") "ground_check" $Air
  $rc[0]; Get-Content "$Log\ground_check.out.txt" | ForEach-Object { $_.Substring(0, [Math]::Min(200, $_.Length)) }
  Get-Content "$Log\ground_check.err.txt" -Tail 5
}
if ((Want "road_wear_check") -and (Test-Path "$Ws\data\road_wear.json")) {
  $rc = Run-Low "python" @("tools/road_wear_check.py", $Ws, "--kn5", "$Ws\build\$slug.kn5", "--json", "$Ws\data\road_wear_check.json") "road_wear_check" $Air
  $rc[0]; Get-Content "$Log\road_wear_check.out.txt" | ForEach-Object { $_.Substring(0, [Math]::Min(420, $_.Length)) }
  Get-Content "$Log\road_wear_check.err.txt" -Tail 5
}
"DONE"
