"""Step B: write the crow logic graphs into BP_CrowAgent and BP_CrowAIController."""
import unreal, sys, os, re, importlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from crow_run import run
import crow_graphs; importlib.reload(crow_graphs)
from editor_toolset.toolsets.blueprint import BlueprintTools as BT

FOLDER = "/Game/Characters/Crow/Blueprints"

def expand(code, prefix="Variables|Default|"):
    code = re.sub(r"\(set! (\w+) ", lambda m: f"({prefix}Set{m.group(1)} ", code)
    code = re.sub(r"\$(\w+)", lambda m: f"({prefix}Get{m.group(1)})", code)
    return code

def var_names(bp):
    return [str(v.name) if hasattr(v, "name") else str(v) for v in BT.list_variables(bp)]

def ensure_fn(bp, name, params):
    if name not in [str(g.get_name()) for g in BT.list_graphs(bp)]:
        BT.add_function_graph(bp, name)
    g = BT.get_graph(bp, name)
    for pname, ptype, is_in in params:
        try:
            BT.add_function_param(g, pname, ptype, is_in)
        except Exception as e:
            print(f"   (param {name}.{pname}: {str(e).splitlines()[0][:120]})")
    return g

def write(graph, label, code):
    try:
        from editor_toolset.toolsets import blueprint_dsl
        blueprint_dsl.Transpiler(
            graph, BT.create_node, BT.connect_pins, BT._get_node_info, BT.set_pin_value,
            lambda g: BT.find_nodes(g), delete_node_fn=BT.delete_node,
            find_node_types_fn=lambda f: BT.find_node_types(graph, f),
        ).transpile(expand(code))
        txt = BT.read_graph_dsl(graph)
        body_lines = [l for l in txt.splitlines() if l.strip() and not l.startswith("(fn ") and not l.startswith("(event ")]
        if len(body_lines) < 2:
            print(f"[FAIL] {label}: graph empty after write (DSL error logged by the editor)\n{txt[:300]}")
            return False
        print(f"[OK] {label} ({len(txt)} chars)")
        return True
    except Exception as e:
        print(f"[FAIL] {label}:\n{e}\n")
        return False

def main():
    crow = unreal.load_asset(f"{FOLDER}/BP_CrowAgent")
    ctrl = unreal.load_asset(f"{FOLDER}/BP_CrowAIController")
    for n, t in [("CurRealm", "int"), ("BestDist", "float"), ("BestLoc", "Vector"), ("Found", "bool"), ("RealmFlag", "bool")]:
        if n not in var_names(ctrl):
            BT.add_variable(ctrl, n, t)
    BT.compile_blueprint(ctrl)

    ok = True
    for name, (params, code) in crow_graphs.CROW_FUNCS.items():
        ok &= write(ensure_fn(crow, name, params), f"crow fn {name}", code)
    ok &= write(BT.get_graph(crow, "EventGraph"), "crow EventGraph", crow_graphs.CROW_EVENTS)
    BT.compile_blueprint(crow)

    # controller wiring on the pawn defaults
    cdo = BT.get_default_object(crow)
    cdo.set_editor_property("ai_controller_class", ctrl.generated_class())
    cdo.set_editor_property("auto_possess_ai", unreal.AutoPossessAI.PLACED_IN_WORLD_OR_SPAWNED)

    cg = BT.get_graph(ctrl, "EventGraph")
    print("ctrl BPCrowAgent nodes:", [n for n in BT.find_node_types(cg, "BPCrowAgent|") if any(k in n for k in ("Flee", "Approach", "GetMode", "SetIsAlert", "SetThreat"))])
    for name, (params, code) in crow_graphs.CTRL_FUNCS.items():
        ok &= write(ensure_fn(ctrl, name, params), f"ctrl fn {name}", code)
    ok &= write(cg, "ctrl EventGraph", crow_graphs.CTRL_EVENTS)

    for bp in (crow, ctrl):
        try:
            BT.compile_blueprint(bp, warnings_as_errors=False)
            print(f"compiled {bp.get_name()}")
        except Exception as e:
            print(f"[COMPILE FAIL] {bp.get_name()}: {e}")
            ok = False
    unreal.EditorAssetLibrary.save_directory("/Game/Characters/Crow", only_if_is_dirty=True, recursive=True)
    print("ALL OK" if ok else "SOME FAILED")

if __name__ == "__main__":
    run("build_b", main)
