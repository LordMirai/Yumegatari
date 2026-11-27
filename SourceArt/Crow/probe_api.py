"""Dumps the editor's Python toolset APIs to Saved/crow_api.txt (read-only probe)."""
import unreal, os, sys, inspect, glob

out = []
def w(s): out.append(str(s))

eng = unreal.Paths.convert_relative_path_to_full(unreal.Paths.engine_plugins_dir())
for d in sorted(glob.glob(os.path.join(eng, "Experimental", "Toolsets", "*"))) + sorted(glob.glob(os.path.join(eng, "*", "*Toolset*"))):
    w(f"== DIR {d}")
    for f in glob.glob(os.path.join(d, "Content", "Python", "**", "*.py"), recursive=True):
        w(f"   file {f}  ({os.path.getsize(f)} bytes)")

w("== sys.modules with toolset/mcp in name")
for name, mod in sorted(sys.modules.items()):
    if any(k in name.lower() for k in ("toolset", "mcp", "agent")):
        w(f"module {name}: {getattr(mod, '__file__', '')}")
        try:
            for n, o in inspect.getmembers(mod):
                if not n.startswith("_") and (inspect.isfunction(o) or inspect.isclass(o)):
                    try: sig = str(inspect.signature(o))
                    except Exception: sig = ""
                    doc = (inspect.getdoc(o) or "").split("\n")[0][:140]
                    w(f"    {n}{sig}  # {doc}")
        except Exception as e:
            w(f"    (error {e})")

w("== unreal classes with Toolset/Blueprint graph/BehaviorTree editing in name")
for n in dir(unreal):
    l = n.lower()
    if any(k in l for k in ("toolset", "mcp", "k2node", "blueprinteditor", "behaviortreeeditor", "blackboardkey", "graphedit", "statetreeeditor", "anim_graph", "animgraph", "animblueprint")):
        w(f"unreal.{n}")
        if "toolset" in l or "library" in l or "subsystem" in l:
            o = getattr(unreal, n)
            for m in dir(o):
                if not m.startswith("_") and callable(getattr(o, m, None)):
                    doc = (getattr(getattr(o, m), "__doc__", "") or "").split("\n")[0][:160]
                    w(f"      .{m}  # {doc}")

path = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()), "crow_api.txt")
open(path, "w", encoding="utf-8").write("\n".join(out))
unreal.log(f"CROW_PROBE wrote {len(out)} lines to {path}")
