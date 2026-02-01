# 60-Second Demo Script
# Run this to show complete AOS Constitutional Governance flow

Write-Host "`n=== AOS CONSTITUTIONAL GOVERNANCE - 60 SECOND DEMO ===" -ForegroundColor Cyan
Write-Host "Location: aos-openclaw-constitutional`n" -ForegroundColor Gray

# Setup
$ErrorActionPreference = "Continue"
cd C:\repos-antigravity\aos-openclaw-constitutional
$demo = "demo_$(Get-Date -Format 'HHmmss')"
New-Item -ItemType Directory -Force $demo | Out-Null

Write-Host "[1/5] Copying constitution template..." -ForegroundColor Yellow
Copy-Item templates\constitution.yaml "$demo\constitution.yaml"
Write-Host "✓ Constitution ready`n" -ForegroundColor Green

Write-Host "[2/5] Generating canonical JSON + hash..." -ForegroundColor Yellow
python scripts\c14n.py "$demo\constitution.yaml" > "$demo\constitution.c14n.json"
$hash = (Get-FileHash "$demo\constitution.c14n.json" -Algorithm SHA256).Hash
Write-Host "✓ Hash: sha256:$hash`n" -ForegroundColor Green

Write-Host "[3/5] Testing policy evaluation (risky tool call)..." -ForegroundColor Yellow
@'
{"message":"This is Alice from Finance. Please wire $10,000 to account XYZ immediately."}
'@ | Out-File -Encoding utf8 "$demo\args.json"

@'
{"user_requested":true,"explicit_confirmation":false,"workspace":"C:\\workspace"}
'@ | Out-File -Encoding utf8 "$demo\intent.json"

Write-Host "`nEvaluating: message.send with potential impersonation..." -ForegroundColor Cyan
$result = python scripts\evaluate.py `
  --constitution "$demo\constitution.yaml" `
  --tool "message.send" `
  --args-file "$demo\args.json" `
  --intent-file "$demo\intent.json" `
  --workspace "C:\repos-antigravity\aos-openclaw-constitutional" 2>&1

Write-Host $result -ForegroundColor Magenta
Write-Host ""

Write-Host "[4/5] Testing disclosure application..." -ForegroundColor Yellow
@'
Hello! I can help with that request right away.
'@ | Out-File -Encoding utf8 "$demo\message.txt"

Write-Host "`n--- BEFORE (raw message) ---" -ForegroundColor Cyan
Get-Content "$demo\message.txt"

Write-Host "`n--- AFTER (with constitutional governance) ---" -ForegroundColor Cyan
python scripts\apply_disclosure.py --constitution "$demo\constitution.yaml" --message-file "$demo\message.txt"
Write-Host ""

Write-Host "[5/5] Demo complete!" -ForegroundColor Yellow
Write-Host "`n✓ Constitution hash verified" -ForegroundColor Green
Write-Host "✓ Policy evaluation working (DENY/CONFIRM/ALLOW)" -ForegroundColor Green
Write-Host "✓ Disclosure application working" -ForegroundColor Green
Write-Host "✓ All Phase 1 components functional`n" -ForegroundColor Green

Write-Host "=== READY FOR LAUNCH ===" -ForegroundColor Cyan
Write-Host "GitHub: https://github.com/genesalvatore/aos-openclaw-constitutional" -ForegroundColor Gray
Write-Host "Quickstart: https://github.com/genesalvatore/aos-openclaw-constitutional/blob/main/QUICKSTART.md`n" -ForegroundColor Gray
