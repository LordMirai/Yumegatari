"""Step B2: (re)write only the controller graphs, verifying they survive compile."""
import unreal, sys, os, re, importlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from crow_run import run
import crow_graphs; importlib.reload(crow_graphs)
import build_b; importlib.reload(build_b)
from editor_toolset.toolsets.blueprint import BlueprintTools as BT

FOLDER = "/Game/Characters/Crow/Blueprints"

def main():
    crow = unreal.load_asset(f"{FOLDER}/BP_CrowAgent")
    ctrl = unreal.load_asset(f"{FOLDER}/BP_CrowAIController")
    # make sure the Crow variable points at the current generated class
    vars_ = build_b.var_names(ctrl)
    print("ctrl vars:", vars_)
    if "Crow" in vars_:
        BT.remove_variable(ctrl, "Crow")
    BT.add_object_variable(ctrl, "Crow", crow.generated_class())
    BT.compile_blueprint(ctrl)
    cg = BT.get_graph(ctrl, "EventGraph")
    for name, (params, code) in crow_graphs.CTRL_FUNCS.items():
        g = build_b.ensure_fn(ctrl, name, params)
        build_b.write(g, f"ctrl fn {name}", code)
        print(f"  after write {name}: {len(BT.read_graph_dsl(g))} chars")
    build_b.write(cg, "ctrl EventGraph", crow_graphs.CTRL_EVENTS)
    print(f"  after write EventGraph: {len(BT.read_graph_dsl(cg))} chars")
    BT.compile_blueprint(ctrl)
    for g in BT.list_graphs(ctrl):
        print(f"--- after compile {g.get_name()}: {len(BT.read_graph_dsl(g))} chars")
    print(BT.read_graph_dsl(cg)[:2500])
    unreal.EditorAssetLibrary.save_asset(ctrl.get_path_name(), only_if_is_dirty=False)

if __name__ == "__main__":
    run("build_b2", main)
