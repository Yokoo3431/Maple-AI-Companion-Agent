# Windows OCR helper (WinRT) - invoked by WindowsOCRProvider
param(
    [Parameter(Mandatory = $true)][string]$ImagePath,
    [string]$Language = "zh-Hans-CN"
)

$ErrorActionPreference = "Stop"

Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime]
$null = [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics, ContentType = WindowsRuntime]
$null = [Windows.Globalization.Language, Windows.Globalization, ContentType = WindowsRuntime]

$asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq "AsTask" -and $_.GetParameters().Count -eq 1 -and
    $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
})[0]

function Await {
    param($WinRtTask, $ResultType)
    $asTask = $asTaskGeneric.MakeGenericMethod($ResultType)
    $netTask = $asTask.Invoke($null, @($WinRtTask))
    $netTask.Wait(-1) | Out-Null
    $netTask.Result
}

try {
    $fileStream = [System.IO.File]::OpenRead($ImagePath)
    $stream = [System.IO.WindowsRuntimeStreamExtensions]::AsRandomAccessStream($fileStream)
    $decoder = Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
    $bitmap = Await ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])

    $engine = $null
    if ($Language) {
        $lang = [Windows.Globalization.Language]::new($Language)
        $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage($lang)
    }
    if ($null -eq $engine) {
        $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
    }
    if ($null -eq $engine) {
        Write-Error "Cannot create OCR engine (language pack missing?)"
        exit 2
    }

    $result = Await ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
    $lineTexts = @()
    $lineBoxes = @()
    foreach ($line in @($result.Lines)) {
        $text = ""
        $lefts = @()
        $tops = @()
        $rights = @()
        $bottoms = @()
        foreach ($word in @($line.Words)) {
            $text += $word.Text
            $rect = $word.BoundingRect
            $lefts += [int]$rect.X
            $tops += [int]$rect.Y
            $rights += [int]($rect.X + $rect.Width)
            $bottoms += [int]($rect.Y + $rect.Height)
        }
        if (-not $text) { continue }
        $lineTexts += $text
        $minLeft = [System.Linq.Enumerable]::Min([int[]]$lefts)
        $minTop = [System.Linq.Enumerable]::Min([int[]]$tops)
        $maxRight = [System.Linq.Enumerable]::Max([int[]]$rights)
        $maxBottom = [System.Linq.Enumerable]::Max([int[]]$bottoms)
        $lineBoxes += @{
            left   = [int]$minLeft
            top    = [int]$minTop
            width  = [int]($maxRight - $minLeft)
            height = [int]($maxBottom - $minTop)
        }
    }
    $left = 0
    $top = 0
    $right = 0
    $bottom = 0
    if ($lineBoxes.Count -gt 0) {
        $allLefts = @()
        $allTops = @()
        $allRights = @()
        $allBottoms = @()
        foreach ($box in $lineBoxes) {
            $allLefts += $box.left
            $allTops += $box.top
            $allRights += ($box.left + $box.width)
            $allBottoms += ($box.top + $box.height)
        }
        $left = [System.Linq.Enumerable]::Min([int[]]$allLefts)
        $top = [System.Linq.Enumerable]::Min([int[]]$allTops)
        $right = [System.Linq.Enumerable]::Max([int[]]$allRights)
        $bottom = [System.Linq.Enumerable]::Max([int[]]$allBottoms)
    }
    [PSCustomObject]@{
        text       = $lineTexts -join "`n"
        bbox       = @{
            left   = [int]$left
            top    = [int]$top
            width  = [int]($right - $left)
            height = [int]($bottom - $top)
        }
        confidence = 1.0
    } | ConvertTo-Json -Compress
} catch {
    $ex = $_.Exception
    while ($ex.InnerException) { $ex = $ex.InnerException }
    Write-Error ("Windows OCR inner error: " + $ex.Message)
    exit 1
}
