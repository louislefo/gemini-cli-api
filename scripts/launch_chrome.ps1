Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Launching Google Chrome with Remote Debugging (Port 9222)" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

$chromePaths = @(
    "C:\Program Files\Google\Chrome\Application\chrome.exe",
    "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"
)

$chromeExe = $null
foreach ($path in $chromePaths) {
    if (Test-Path $path) {
        $chromeExe = $path
        break
    }
}

if (-not $chromeExe) {
    Write-Host "[ERROR] Could not find chrome.exe." -ForegroundColor Red
    exit 1
}

$userDataDir = "$env:USERPROFILE\.chrome_gemini_profile"

Write-Host "Chrome Path : $chromeExe" -ForegroundColor Green
Write-Host "Profile Dir : $userDataDir" -ForegroundColor Green
Write-Host "CDP Port    : 9222" -ForegroundColor Green
Write-Host "Target URL  : https://gemini.google.com/app`n" -ForegroundColor Green

Start-Process -FilePath $chromeExe -ArgumentList "--remote-debugging-port=9222", "--user-data-dir=`"$userDataDir`"", "https://gemini.google.com/app"

Write-Host "Browser launched successfully." -ForegroundColor Yellow
Write-Host "Please log in to Gemini if prompted, then start the FastAPI API / CLI." -ForegroundColor Yellow

