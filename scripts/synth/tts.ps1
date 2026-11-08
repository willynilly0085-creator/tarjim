# Batch TTS with the offline OneCore voices (WinRT SpeechSynthesizer).
# Jobs file: JSON list of {voice, pitch, rate, text, wav, json}. For each job it writes
# the 16 kHz mono WAV and a JSON list of word boundaries {text, start, pos} in seconds.
param([string]$Jobs)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Media.SpeechSynthesis.SpeechSynthesizer, Windows.Media.SpeechSynthesis, ContentType = WindowsRuntime]
$null = [Windows.Storage.Streams.DataReader, Windows.Storage.Streams, ContentType = WindowsRuntime]
$asTask = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and
    $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' })[0]
function Await($op, [Type]$t) {
    $task = $asTask.MakeGenericMethod($t).Invoke($null, @($op)); $task.Wait(-1) | Out-Null; $task.Result
}
$utf8 = New-Object Text.UTF8Encoding($false)
$all = [Windows.Media.SpeechSynthesis.SpeechSynthesizer]::AllVoices
$synth = New-Object Windows.Media.SpeechSynthesis.SpeechSynthesizer
$synth.Options.IncludeWordBoundaryMetadata = $true
$list = [IO.File]::ReadAllText($Jobs, $utf8) | ConvertFrom-Json
foreach ($job in @($list)) {
    $v = $all | Where-Object { $_.Id -like "*$($job.voice)*" } | Select-Object -First 1
    if (-not $v) { throw "voice not found: $($job.voice)" }
    $synth.Voice = $v
    $synth.Options.AudioPitch = [double]$job.pitch
    $synth.Options.SpeakingRate = [double]$job.rate
    $stream = Await ($synth.SynthesizeTextToStreamAsync($job.text)) ([Windows.Media.SpeechSynthesis.SpeechSynthesisStream])
    $words = @()
    foreach ($track in $stream.TimedMetadataTracks) {
        if ($track.Id -ne 'SpeechWord') { continue }
        foreach ($cue in $track.Cues) {
            $words += [pscustomobject]@{ text = $cue.Text; start = $cue.StartTime.TotalSeconds;
                pos = $cue.StartPositionInInput }
        }
    }
    $size = [uint32]$stream.Size
    $reader = New-Object Windows.Storage.Streams.DataReader($stream.GetInputStreamAt(0))
    $null = Await ($reader.LoadAsync($size)) ([uint32])
    $bytes = New-Object byte[] $size
    $reader.ReadBytes($bytes)
    [IO.File]::WriteAllBytes($job.wav, $bytes)
    [IO.File]::WriteAllText($job.json, (ConvertTo-Json -InputObject @($words) -Depth 3), $utf8)
}
