import json

r = json.load(open("scripts/audit_scan_report.json"))

print("=" * 80)
print("ZOHRA AST AUDIT SCANNER -- DETAILED RESULTS")
print("=" * 80)

print(f"\n{'='*80}")
print("SUMMARY")
print(f"{'='*80}")
for k, v in r["summary"].items():
    print(f"  {k}: {v}")

print(f"\n{'='*80}")
print(f"KEYWORD MATCHES ({len(r['keywords'])} found)")
print(f"{'='*80}")
for x in r["keywords"]:
    print(f"  {x['file']}:{x['line']}  [{x['keyword']}]")
    print(f"    -> {x['content'][:150]}")

print(f"\n{'='*80}")
print(f"EMPTY / PASS-ONLY FUNCTIONS ({len(r['empty_functions'])} found)")
print(f"{'='*80}")
if not r["empty_functions"]:
    print("  [OK] NONE -- Zero empty/stub functions in production code")
else:
    for x in r["empty_functions"]:
        print(f"  {x['file']}:{x['line']}  {x['name']}  type={x['type']}")

print(f"\n{'='*80}")
print(f"SWALLOWED EXCEPTIONS -- silent pass ({len(r['swallowed_exceptions'])} found)")
print(f"{'='*80}")
if not r["swallowed_exceptions"]:
    print("  [OK] NONE")
else:
    for x in r["swallowed_exceptions"]:
        print(f"  {x['file']}:{x['line']}  type={x['type']}")

print(f"\n{'='*80}")
print(f"BROAD UNLOGGED EXCEPTIONS ({len(r['broad_unlogged_exceptions'])} found)")
print(f"{'='*80}")
if not r["broad_unlogged_exceptions"]:
    print("  [OK] NONE")
else:
    for x in r["broad_unlogged_exceptions"]:
        print(f"  {x['file']}:{x['line']}  type={x['type']}")

print(f"\n{'='*80}")
print(f"API ROUTES ({len(r['routes'])} endpoints)")
print(f"{'='*80}")
for x in r["routes"]:
    print(f"  {x['method']:6s} {(x['path'] or '(prefix-relative)'):40s}  -> {x['name']}  ({x['file']}:{x['line']})")

print(f"\n{'='*80}")
print(f"DATABASE MODELS ({len(r['db_models'])} models)")
print(f"{'='*80}")
for x in r["db_models"]:
    tbl = x["tablename"] or "(no __tablename__)"
    print(f"  {x['class']:40s}  table={tbl:30s}  ({x['file']}:{x['line']})")

print(f"\n{'='*80}")
print("SCAN COMPLETE")
print(f"{'='*80}")
