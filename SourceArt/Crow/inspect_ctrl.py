import unreal, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from crow_run import run
from editor_toolset.toolsets.blueprint import BlueprintTools as BT

def main():
    for path in ["/Game/Characters/Crow/Blueprints/BP_CrowAIController", "/Game/Characters/Crow/Blueprints/BP_CrowAgent"]:
        bp = unreal.load_asset(path)
        print("=" * 30, bp.get_name(), "status:", bp.get_editor_property("status") if hasattr(bp, "get_editor_property") else "?")
        for g in BT.list_graphs(bp):
            print("--- graph", g.get_name())
            try:
                print(BT.read_graph_dsl(g)[:3500])
            except Exception as e:
                print("read err", e)
        print("events implemented:", [str(e.name) for e in BT.list_events(bp) if e.is_implemented])

run("inspect_ctrl", main)
