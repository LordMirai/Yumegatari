import unreal, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from crow_run import run
from editor_toolset.toolsets.blueprint import BlueprintTools as BT

QUERIES = [
    "GetPlayerPawn", "GetActorLocation", "SetActorLocation", "SetActorRotation", "GetActorRotation",
    "GetVelocity", "VectorLength", "Distance", "RInterpTo", "VInterpTo", "FindLookatRotation", "Lerp",
    "RandomFloatInRange", "RandomIntegerInRange", "Delay", "PlayAnimation", "GetAllActorsOfClass",
    "GetWorldDeltaSeconds", "GetControlledPawn", "CastToBP_Crow", "sin", "cos", "SetTimerbyEvent",
    "SetTimerbyFunctionName", "ClearTimer", "Normal", "GetForwardVector", "MakeRotator", "FInterpTo",
    "EaseFunction|", "Ease", "SetVisibility", "PrintString", "IsValid", "SetActorTickEnabled",
    "GetActorForwardVector", "GetGameTimeinSeconds", "MapRangeClamped", "Clamp", "Atan2", "Select",
    "SetActorRotation", "SetWorldRotation", "SetRelativeRotation", "K2_SetActorLocationAndRotation",
    "SetActorLocationAndRotation", "GetSpeed", "VSize", "LineTraceByChannel", "RandomUnitVector",
    "RandomPointInBoundingBox", "SpawnDefaultController", "SetSkeletalMesh", "Get Owner",
]

def main():
    bp = unreal.load_asset("/Game/Characters/Crow/_Scratch/BP_Scratch")
    if not bp:
        bp = BT.create("/Game/Characters/Crow/_Scratch", "BP_Scratch", unreal.Pawn.static_class())
    g = BT.get_graph(bp, "EventGraph")
    for q in QUERIES:
        try:
            res = BT.find_node_types(g, q)
        except Exception as e:
            res = [f"ERR {e}"]
        print(f"## {q}: {len(res)}")
        for r in res[:14]:
            print("   ", r)
    # controller graph too
    cbp = unreal.load_asset("/Game/Characters/Crow/_Scratch/BP_ScratchCtrl")
    if not cbp:
        cbp = BT.create("/Game/Characters/Crow/_Scratch", "BP_ScratchCtrl", unreal.AIController.static_class())
    cg = BT.get_graph(cbp, "EventGraph")
    for q in ["GetControlledPawn", "GetPawn", "MoveToLocation", "Possess", "ReceivePossess", "OnPossess", "EventTick", "Event Tick", "AddEvent|"]:
        res = BT.find_node_types(cg, q)
        print(f"## [ctrl] {q}: {len(res)}")
        for r in res[:20]:
            print("   ", r)
    print("## events pawn:", [str(e.name) for e in BT.list_events(bp)][:60])
    print("## events ctrl:", [str(e.name) for e in BT.list_events(cbp)][:60])

run("probe_nodes", main)
