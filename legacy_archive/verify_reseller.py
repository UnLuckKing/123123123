import re

with open("reseller_portal_dump.html", "r", encoding="utf-8") as f:
    html = f.read()

# Find all getElementById in script
element_ids_referenced = re.findall(r"document\.getElementById\(['\"]([^'\"]+)['\"]\)", html)
# Find all id="..." in html
element_ids_defined = set(re.findall(r'id=["\']([^"\']+)["\']', html))

print("Referenced IDs in JS:", len(element_ids_referenced))
missing = [eid for eid in element_ids_referenced if eid not in element_ids_defined]
print("MISSING DOM IDs referenced in JS:", set(missing))

# Also search for all onclick handlers
onclicks = re.findall(r'onclick=["\']([^"\']+)["\']', html)
print("\nOnclick handlers:", set(onclicks))

# Also search for all functions defined in <script>
functions_defined = re.findall(r'(?:function|async function)\s+([a-zA-Z0-9_]+)\s*\(', html)
print("\nFunctions defined in script:", functions_defined)
