# Build script to update vanta_hub.py with complete 3-Tier Multi-Tenant Architecture
import re

hub_path = r"C:\Users\hesap\Desktop\nrx.lol-main\server\vanta_hub.py"

with open(hub_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Fix the missing closing </div> for tab-audit in HTML_DASHBOARD
old_audit_close = """                    <tbody id="logsTable">
                        <tr><td colspan="6" style="text-align:center; color:var(--text-dim);">Loading audit records...</td></tr>
                    </tbody>
                </table>
        </div>

        <!-- TAB 5: Reseller Hub -->"""

new_audit_close = """                    <tbody id="logsTable">
                        <tr><td colspan="6" style="text-align:center; color:var(--text-dim);">Loading audit records...</td></tr>
                    </tbody>
                </table>
            </div>
        </div>

        <!-- TAB 5: Reseller Hub -->"""

if old_audit_close in content:
    content = content.replace(old_audit_close, new_audit_close)
    print("[SUCCESS] Fixed tab-audit unclosed div!")
else:
    print("[WARN] old_audit_close pattern not found verbatim, checking regex...")
    pattern = r'(<tbody id="logsTable">.*?</table>\s*</div>)(\s*<!-- TAB 5: Reseller Hub -->)'
    if re.search(pattern, content, re.DOTALL):
        content = re.sub(pattern, r'\1\n        </div>\2', content, flags=re.DOTALL)
        print("[SUCCESS] Fixed tab-audit unclosed div via regex!")
    else:
        print("[FAIL] Could not match tab-audit closure pattern.")

with open(hub_path, "w", encoding="utf-8") as f:
    f.write(content)
print("[OK] Finished phase 1.")
