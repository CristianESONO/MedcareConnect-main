[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$response = Invoke-WebRequest -Uri 'https://app.medcare.sn/' -TimeoutSec 20 -SkipCertificateCheck -ErrorAction Stop
$html = $response.Content
Write-Host "HTML Length: $($html.Length)"
Write-Host "Contains 'hematologie': $(if ($html -like '*hematologie*') { 'YES' } else { 'NO' })"
Write-Host "Contains 'hemostase': $(if ($html -like '*hemostase*') { 'YES' } else { 'NO' })"
Write-Host "Contains 'hématologie': $(if ($html -like '*hématologie*') { 'YES' } else { 'NO' })"
Write-Host "Contains 'hémostase': $(if ($html -like '*hémostase*') { 'YES' } else { 'NO' })"
Write-Host "Contains 'biologie': $(if ($html -like '*biologie*') { 'YES' } else { 'NO' })"
Write-Host "Contains 'imagerie': $(if ($html -like '*imagerie*') { 'YES' } else { 'NO' })"
Write-Host "Contains 'les 6 piliers': $(if ($html -like '*les 6 piliers*' -or $html -like '*6 piliers*') { 'YES' } else { 'NO' })"
