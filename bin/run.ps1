# ensure this runs even under restrictive policies
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force

# resolve script folder
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition

# parent of the bin/ folder
$RootDir = Split-Path -Parent $ScriptDir

# paths in the project root
$VenvDir  = Join-Path $RootDir '.venv'
$ReqFile  = Join-Path $RootDir 'requirements.txt'
$MainFile = Join-Path $RootDir 'main.py'
# create venv if missing
if (-Not (Test-Path $VenvDir)) {
    Write-Host "Creating virtual environment in $VenvDir..."
    python -m venv $VenvDir
}

# activate
Write-Host "Activating virtual environment..."
& (Join-Path $VenvDir 'Scripts\Activate.ps1')

# install deps
Write-Host "Installing requirements from $ReqFile..."
pip install -r $ReqFile

# launch
Write-Host "Starting $MainFile..."
python $MainFile
