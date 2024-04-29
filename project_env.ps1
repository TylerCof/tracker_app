# run using '. .\project_env.ps1' or '.\project_env.ps1'

$env:SECRET_KEY = "YOUR_SECRET_KEY_HERE"
$env:FLASK_ENV = "development"

. "env/Scripts/Activate.ps1"

function global:run-server {
	python -m tracker.server
}

function global:_INNER_DEACTIVATE { "" }
Copy-Item -Path function:deactivate -Destination function:_INNER_DEACTIVATE

function global:deactivate {
	Remove-Item -Path Env:SECRET_KEY
	Remove-Item -Path Env:FLASK_ENV

	Remove-Item -Path function:run-server

	Copy-Item -Path function:_INNER_DEACTIVATE -Destination function:deactivate
	Remove-Item -Path function:_INNER_DEACTIVATE

	deactivate
}
