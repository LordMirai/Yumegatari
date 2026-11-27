"""Shared runner: executes a crow build step and writes its output/errors to Saved/crow_out_<step>.txt"""
import unreal, os, traceback, io, contextlib, importlib, sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

def run(step_name, fn):
    saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
    path = os.path.join(saved, f"crow_out_{step_name}.txt")
    buf = io.StringIO()
    ok = True
    try:
        with contextlib.redirect_stdout(buf):
            fn()
    except Exception:
        ok = False
        buf.write("\n!!! EXCEPTION\n" + traceback.format_exc())
    buf.write(f"\n=== {'OK' if ok else 'FAILED'} ===\n")
    open(path, "w", encoding="utf-8").write(buf.getvalue())
    unreal.log(f"CROW_STEP {step_name} {'OK' if ok else 'FAILED'} -> {path}")
