@echo off
:: Set Google API Key path
:: Set path variable

    set API_KEY_PATH=C:\Users\Public\CLOUD-PROJECT-825e415d90d0.json
    setx GOOGLE_APPLICATION_CREDENTIALS "%API_KEY_PATH%" /m
    echo %GOOGLE_APPLICATION_CREDENTIALS%

pause