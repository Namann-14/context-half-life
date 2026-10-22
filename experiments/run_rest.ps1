# E3 reader part, then E4/E5 answers, then the judge. One request at a time (llama3.2:3b, then qwen2.5:3b).
$ErrorActionPreference = "Stop"
$py = Join-Path $PSScriptRoot "..\.venv\Scripts\python.exe"
$env:OLLAMA_NUM_PARALLEL = "1"; $env:OLLAMA_MAX_LOADED_MODELS = "1"
& $py "$PSScriptRoot\e3_injection.py" --model llama3.2:3b
& $py "$PSScriptRoot\e4_repair.py" --stage answer
& $py "$PSScriptRoot\e4_repair.py" --stage judge
& $py "$PSScriptRoot\analyze.py"
