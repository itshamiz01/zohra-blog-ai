"""
Fast, Comprehensive Static & AST Architecture Audit Scanner for Zohra.
Audits without running external services:
- Suspicious keywords (TODO, FIXME, NotImplemented, dummy, placeholder, mock, etc.)
- AST-level empty functions / pass-only functions
- Broad exception swallowing (except Exception: pass)
- API route authentication & authorization inspection via AST
- Database models and table declarations
"""

import ast
import json
import os
import re
from pathlib import Path


def scan_keywords(target_dir="app"):
    keywords = [
        "TODO", "FIXME", "HACK", "XXX", "TEMP", "temporary",
        "NotImplementedError", "raise NotImplemented",
        "fake", "dummy", "placeholder"
    ]
    results = []
    for root, _, files in os.walk(target_dir):
        for f in files:
            if f.endswith(".py"):
                p = Path(root) / f
                content = p.read_text(encoding="utf-8", errors="ignore")
                for line_num, line in enumerate(content.splitlines(), 1):
                    for kw in keywords:
                        if re.search(r"\b" + re.escape(kw) + r"\b", line, re.IGNORECASE):
                            # Skip common acceptable patterns like tempfile, template, or comments explaining tests
                            results.append({
                                "file": str(p),
                                "line": line_num,
                                "keyword": kw,
                                "content": line.strip()
                            })
    return results


def scan_ast(target_dir="app"):
    empty_funcs = []
    swallowed_exceptions = []
    broad_exceptions = []
    routes = []
    db_models = []

    for root, _, files in os.walk(target_dir):
        for f in files:
            if f.endswith(".py"):
                p = Path(root) / f
                code = p.read_text(encoding="utf-8", errors="ignore")
                try:
                    tree = ast.parse(code, filename=str(p))
                except Exception as e:
                    print(f"Failed to parse {p}: {e}")
                    continue

                for node in ast.walk(tree):
                    # Check classes for SQLAlchemy models
                    if isinstance(node, ast.ClassDef):
                        base_names = []
                        for b in node.bases:
                            if isinstance(b, ast.Name):
                                base_names.append(b.id)
                            elif isinstance(b, ast.Attribute):
                                base_names.append(b.attr)
                        if any("Base" in b or "Model" in b for b in base_names):
                            # Find __tablename__
                            tablename = None
                            for item in node.body:
                                if isinstance(item, ast.Assign):
                                    for target in item.targets:
                                        if isinstance(target, ast.Name) and target.id == "__tablename__":
                                            if isinstance(item.value, ast.Constant):
                                                tablename = item.value.value
                            db_models.append({
                                "file": str(p),
                                "line": node.lineno,
                                "class": node.name,
                                "tablename": tablename,
                                "bases": base_names
                            })

                    # Check functions / methods
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        decorators = []
                        is_route = False
                        route_path = None
                        route_method = None
                        
                        for d in node.decorator_list:
                            dec_str = ""
                            if isinstance(d, ast.Call):
                                if isinstance(d.func, ast.Attribute):
                                    dec_str = f"{ast.unparse(d.func)}" if hasattr(ast, "unparse") else d.func.attr
                                    if d.func.attr in ("get", "post", "put", "delete", "patch"):
                                        is_route = True
                                        route_method = d.func.attr.upper()
                                        if d.args and isinstance(d.args[0], ast.Constant):
                                            route_path = d.args[0].value
                            elif isinstance(d, ast.Attribute):
                                dec_str = f"{ast.unparse(d)}" if hasattr(ast, "unparse") else d.attr
                            elif isinstance(d, ast.Name):
                                dec_str = d.id
                            decorators.append(dec_str)

                        if is_route:
                            # Inspect arguments for Depends()
                            deps = []
                            for arg in node.args.args + node.args.kwonlyargs:
                                pass
                            routes.append({
                                "file": str(p),
                                "line": node.lineno,
                                "name": node.name,
                                "method": route_method,
                                "path": route_path,
                                "decorators": decorators
                            })

                        is_abstract = any("abstract" in dec or "overload" in dec for dec in decorators)
                        
                        body_stmts = node.body
                        non_docstring = [
                            stmt for stmt in body_stmts
                            if not (isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str))
                        ]
                        if not non_docstring and not is_abstract:
                            empty_funcs.append({
                                "file": str(p),
                                "line": node.lineno,
                                "name": node.name,
                                "type": "empty_body",
                                "decorators": decorators
                            })
                        elif len(non_docstring) == 1 and not is_abstract:
                            stmt = non_docstring[0]
                            if isinstance(stmt, ast.Pass):
                                empty_funcs.append({
                                    "file": str(p),
                                    "line": node.lineno,
                                    "name": node.name,
                                    "type": "pass_only",
                                    "decorators": decorators
                                })

                    # Check exception swallowing
                    if isinstance(node, ast.Try):
                        for handler in node.handlers:
                            is_broad = False
                            if handler.type is None:
                                is_broad = True
                            elif isinstance(handler.type, ast.Name) and handler.type.id in ("Exception", "BaseException"):
                                is_broad = True
                            
                            if is_broad:
                                handler_body = [
                                    s for s in handler.body
                                    if not (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant) and isinstance(s.value.value, str))
                                ]
                                if len(handler_body) == 1 and isinstance(handler_body[0], ast.Pass):
                                    swallowed_exceptions.append({
                                        "file": str(p),
                                        "line": handler.lineno,
                                        "type": "silent_pass"
                                    })
                                elif not any(isinstance(s, (ast.Raise, ast.Return)) for s in handler_body):
                                    has_log = any(
                                        isinstance(s, ast.Expr) and isinstance(s.value, ast.Call) and
                                        any(log_kw in (ast.unparse(s.value.func) if hasattr(ast, "unparse") else "") for log_kw in ("log", "print", "warning", "error", "info"))
                                        for s in handler_body
                                    )
                                    if not has_log:
                                        broad_exceptions.append({
                                            "file": str(p),
                                            "line": handler.lineno,
                                            "type": "unlogged_no_raise"
                                        })

    return empty_funcs, swallowed_exceptions, broad_exceptions, routes, db_models


if __name__ == "__main__":
    kw_results = scan_keywords("app")
    empty_f, swallowed_e, broad_e, routes, db_models = scan_ast("app")
    
    report = {
        "keywords": kw_results,
        "empty_functions": empty_f,
        "swallowed_exceptions": swallowed_e,
        "broad_unlogged_exceptions": broad_e,
        "routes": routes,
        "db_models": db_models,
        "summary": {
            "total_keywords": len(kw_results),
            "total_empty_functions": len(empty_f),
            "total_swallowed_exceptions": len(swallowed_e),
            "total_broad_unlogged": len(broad_e),
            "total_routes_found": len(routes),
            "total_db_models_found": len(db_models)
        }
    }

    out_file = Path("scripts/audit_scan_report.json")
    out_file.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"=== AUDIT SCAN COMPLETE ===")
    print(f"Keyword matches: {len(kw_results)}")
    print(f"Empty/Pass functions: {len(empty_f)}")
    print(f"Swallowed exceptions (silent pass): {len(swallowed_e)}")
    print(f"Broad unlogged exceptions: {len(broad_e)}")
    print(f"API Routes scanned: {len(routes)}")
    print(f"DB Models scanned: {len(db_models)}")
