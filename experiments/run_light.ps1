# Sequential, single-process run of E1 and E2 with the llama3.2:3b reader (one request at a time).
$ErrorActionPreference = "Stop"
$py = Join-Path $PSScriptRoot "..\.venv\Scripts\python.exe"
$env:OLLAMA_NUM_PARALLEL = "1"; $env:OLLAMA_MAX_LOADED_MODELS = "1"
& $py "$PSScriptRoot\e1_niah.py" --model llama3.2:3b
& $py "$PSScriptRoot\e2_halflife.py" --model llama3.2:3b --mode ageing --facts 20
& $py "$PSScriptRoot\e2_halflife.py" --model llama3.2:3b --mode matched --facts 10
