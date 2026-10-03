import os
import re

with open('launcher_windows.go', 'r', encoding='utf-8') as f:
    code = f.read()

# I will replace the corrupted nested if-else with just cleanArgs = append(cleanArgs, arg)
bad_block = """				if strings.HasPrefix(arg, "-RiotClientPort=") {
			cleanArgs = append(cleanArgs, fmt.Sprintf("-RiotClientPort=%d", proxyPort))
		} else {
			cleanArgs = append(cleanArgs, arg)
		}"""

code = code.replace(bad_block, "				cleanArgs = append(cleanArgs, arg)")

bad_block_2 = """			if strings.HasPrefix(arg, "-RiotClientPort=") {
			cleanArgs = append(cleanArgs, fmt.Sprintf("-RiotClientPort=%d", proxyPort))
		} else {
			cleanArgs = append(cleanArgs, arg)
		}"""

code = code.replace(bad_block_2, "			cleanArgs = append(cleanArgs, arg)")

with open('launcher_windows.go', 'w', encoding='utf-8') as f:
    f.write(code)
