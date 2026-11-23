# After run_full.ps1 (the road kn5 is exported): the chain's street gates and the Speedway's (race_cw, on the lap `college`:
# the layout that drives College's northbound road), by tools/ship_track.sh's own commands. A gate's exit code is printed,
# never a reason to stop: every gate is read. One Blender at a time, below normal. Not run here: race_acw and the north
# layouts' gates, the whole of verify_kn5, the AI lines, TreeFX, the track folder: those are the rehearsal's.
#   powershell -File run_gates.ps1 -Ws <workshop> -Eng <an engine-july copy> [-From <step>] [-To <step>] [-Log <dir>]
param([Parameter(Mandatory = $true)][string]$Ws, [Parameter(Mandatory = $true)][string]$Eng, [string]$From = "export_street", [string]$To = "",
      [string]$Air = "", [string]$Log = "", [string]$Blender = "C:\Program Files\Blender Foundation\Blender 4.2\blender.exe")
if (-not $Air) { $Air = (Resolve-Path "$PSScriptRoot\..\..\..\..\..").Path }
if (-not $Log) { $Log = "$Ws\_scratch_log" }
$slug = "san_diego_lake_murray"
New-Item -ItemType Directory -Force $Log | Out-Null
$order = @("export_street", "road_obj", "ground_check_street", "drive_street", "audit_street",
           "export_race_college", "export_closure_race_cw", "obj_race_cw", "drive_race_cw", "audit_race_cw", "no_route_race_cw", "ground_check_race_cw")
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
function Gate($tag, $exe, $argList, $tail, $cwd) {
  if (-not (Want $tag)) { return }
  $rc = Run-Low $exe $argList $tag $cwd
  $rc[0]
  Get-Content "$Log\$tag.out.txt" | Where-Object { $_ -notmatch "drive-time\] sweep" } | Select-Object -Last $tail | ForEach-Object { $_.Substring(0, [Math]::Min(230, $_.Length)) }
  if ($rc[-1] -ne 0) { Get-Content "$Log\$tag.err.txt" -Tail 6 }
}
function Export($tag, $blend, $out) {
  if (-not (Want $tag)) { return }
  $rc = Run-Low $Blender @("--background", "--python-exit-code", "1", "--python", "$Eng\scripts\ac\export_kn5_addon.py", "--", $Ws, "--blend", "$Ws\blender\split\$blend", "--out", $out) $tag $Ws
  $rc[0]; Get-Content "$Log\$tag.out.txt" | Select-String "KN5 EXISTS|Error|Traceback" | ForEach-Object { $_.Line }
  if ($rc[-1] -ne 0) { "STOP at $tag"; Get-Content "$Log\$tag.err.txt" -Tail 12; exit 1 }
}
Export "export_street" "loop_street.blend" "${slug}_street.kn5"
Gate "road_obj" "python" @("-m", "scripts.modkit.kn5_to_gate_obj", $Ws, "--kn5", "$Ws\build\$slug.kn5", "--kn5", "$Ws\build\${slug}_street.kn5") 3 $Air
Gate "ground_check_street" "python" @("-m", "scripts.ac.kn5_ground_check", $Ws, "--kn5", "$Ws\build\${slug}_street.kn5", "--json", "$Ws\data\kn5_ground_check.street.json") 14 $Air
Gate "drive_street" "python" @("-m", "scripts.geometry.drive_test", $Ws, "--layout", "street") 30 $Air
Gate "audit_street" "python" @("-m", "scripts.geometry.audit_mesh", $Ws) 16 $Air
Export "export_race_college" "loop_race_college.blend" "${slug}_race_college.kn5"
Export "export_closure_race_cw" "loop_closure_race_cw.blend" "${slug}_closure_race_cw.kn5"
Gate "obj_race_cw" "python" @("-m", "scripts.modkit.kn5_to_gate_obj", $Ws, "--kn5", "$Ws\build\$slug.kn5", "--kn5", "$Ws\build\${slug}_race_college.kn5", "--kn5", "$Ws\build\${slug}_closure_race_cw.kn5", "--out", "$Ws\data\track.race_cw.obj") 3 $Air
Gate "drive_race_cw" "python" @("-m", "scripts.geometry.drive_test", $Ws, "--layout", "race_cw") 40 $Air
Gate "audit_race_cw" "python" @("-m", "scripts.geometry.audit_mesh", $Ws, "--layout", "race_cw") 18 $Air
Gate "no_route_race_cw" "python" @("tools/no_route.py", $Ws, "--layout", "race_cw") 12 $Air
Gate "ground_check_race_cw" "python" @("-m", "scripts.ac.kn5_ground_check", $Ws, "--kn5", "$Ws\build\${slug}_race_college.kn5", "--kn5", "$Ws\build\${slug}_closure_race_cw.kn5", "--json", "$Ws\data\kn5_ground_check.race_cw.json") 14 $Air
"DONE"
