# Auto Git Push Script for 'myboomstick' - No typing needed

# ==== CONFIG ====
$repoPath = "C:\Users\Gimp\Documents\myboomstick"
$branchName = "main"
$commitMsg = "Finalized system diagnostics tool with logging and driver checks"

# ==== SCRIPT ====
cd $repoPath

# Initialize git repo if needed (silent fail if already a repo)
if (-not (Test-Path "$repoPath\.git")) {
    git init
    Write-Output "Initialized empty Git repository."
}

git add .
git commit -m "$commitMsg"
git push origin $branchName
