#!/bin/bash
# Vanta LeagueClient Interceptor Wrapper (v6.0 Apex)

ARGS=()
SLOT_NUM=${VANTA_SLOT_NUM:-0}

for arg in "$@"; do
    if [[ $arg == --riotgamesapi-settings=* ]]; then
        MODIFIED_ARG=$(/usr/bin/python3 /Users/m1/modify_settings.py "$arg" 2>/dev/null)
        if [ -n "$MODIFIED_ARG" ]; then
            ARGS+=("$MODIFIED_ARG")
        else
            ARGS+=("$arg")
        fi
    else
        ARGS+=("$arg")
    fi
done

if [ "$SLOT_NUM" != "0" ]; then
    DATA_DIR="/Users/m1/VantaSlots/slot${SLOT_NUM}"
    mkdir -p "$DATA_DIR/CEF" "$DATA_DIR/Logs"
    ARGS+=("--user-data-dir=$DATA_DIR/CEF")
    ARGS+=("--log-dir=$DATA_DIR/Logs")
fi

# Always append --allow-multiple-clients
ARGS+=("--allow-multiple-clients")

exec "/Applications/League of Legends.app/Contents/LoL/LeagueClient.app/Contents/MacOS/LeagueClient_bin" "${ARGS[@]}"
