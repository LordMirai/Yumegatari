"""Step A: create the crow agent assets (empty logic) and probe node IDs that depend on them."""
import unreal, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from crow_run import run
from editor_toolset.toolsets.blueprint import BlueprintTools as BT

FOLDER = "/Game/Characters/Crow/Blueprints"
EAL = unreal.EditorAssetLibrary

def get_or_create(name, parent):
    p = f"{FOLDER}/{name}"
    if EAL.does_asset_exist(p):
        return unreal.load_asset(p)
    return BT.create(FOLDER, name, parent.static_class())

def add_component(bp, cls, name, parent_handle=None):
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    handles = sds.k2_gather_subobject_data_for_blueprint(bp)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    for h in handles:
        obj = lib.get_object(lib.get_data(h))
        if obj and obj.get_name().startswith(name):
            return obj
    params = unreal.AddNewSubobjectParams(parent_handle=parent_handle or handles[0], new_class=cls, blueprint_context=bp)
    h, fail = sds.add_new_subobject(params)
    if not fail.is_empty():
        raise RuntimeError(f"add component {name}: {fail}")
    sds.rename_subobject(h, unreal.Text(name))
    return lib.get_object(lib.get_data(h))

def ensure_var(bp, name, typ, default=None):
    existing = [str(v.name) if hasattr(v, "name") else str(v) for v in BT.list_variables(bp)]
    if name not in existing:
        if isinstance(typ, str):
            BT.add_variable(bp, name, typ)
        else:
            BT.add_object_variable(bp, name, typ)

def main():
    # ---- perch
    perch = get_or_create("BP_CrowPerch", unreal.Actor)
    arrow = add_component(perch, unreal.ArrowComponent, "Facing")
    arrow.set_editor_property("arrow_color", unreal.Color(40, 40, 255, 255))
    arrow.set_editor_property("arrow_size", 0.6)
    bb = add_component(perch, unreal.BillboardComponent, "Icon")
    BT.compile_blueprint(perch)

    # ---- body
    crow = get_or_create("BP_CrowAgent", unreal.Pawn)
    mesh = add_component(crow, unreal.SkeletalMeshComponent, "CrowMesh")
    sk = unreal.load_asset("/Game/Characters/Crow/Mesh/SK_Crow")
    try:
        mesh.set_editor_property("skeletal_mesh_asset", sk)
    except Exception:
        mesh.set_skeletal_mesh_asset(sk)
    mesh.set_editor_property("relative_rotation", unreal.Rotator(0, 0, -90))  # (roll, pitch, yaw) -> yaw -90
    mesh.set_editor_property("animation_mode", unreal.AnimationMode.ANIMATION_SINGLE_NODE)
    mesh.set_collision_profile_name("NoCollision")
    print("mesh rot", mesh.get_editor_property("relative_rotation"))
    for n, t in [("Mode", "int"), ("AnimState", "int"), ("HomeLocation", "Vector"), ("PerchLocation", "Vector"),
                 ("PerchYaw", "float"), ("MoveStart", "Vector"), ("MoveEnd", "Vector"), ("MoveAlpha", "float"),
                 ("MoveDuration", "float"), ("CircleCenter", "Vector"), ("CircleAngle", "float"),
                 ("CircleRadius", "float"), ("CircleTime", "float"), ("FlySpeed", "float"), ("IsGliding", "bool"),
                 ("GlideTimer", "float"), ("PeckTimer", "float"), ("ThreatLocation", "Vector"),
                 ("LookTarget", "Vector"), ("IsAlert", "bool"), ("LandElapsed", "float")]:
        ensure_var(crow, n, t)
    for fn in ["SetAnim", "ReturnToIdle", "FaceTowards"]:
        if fn not in [str(g.get_name()) for g in BT.list_graphs(crow)]:
            BT.add_function_graph(crow, fn)
    for ev in ["FleeFrom", "StartApproach"]:
        BT.add_event(crow, ev)
    BT.compile_blueprint(crow)

    # ---- brain
    ctrl = get_or_create("BP_CrowAIController", unreal.AIController)
    ensure_var(ctrl, "Crow", unreal.load_asset(f"{FOLDER}/BP_CrowAgent").generated_class())
    for n, t in [("AlertRadius", "float"), ("CalmFleeRadius", "float"), ("RunFleeRadius", "float"),
                 ("RunSpeed", "float"), ("LandSafeRadius", "float"), ("LastRealm", "int")]:
        ensure_var(ctrl, n, t)
    BT.compile_blueprint(ctrl)

    # ---- probes
    g = BT.get_graph(crow, "EventGraph")
    for q in ["CrowMesh", "Variables|Default|GetMode", "Variables|Default|SetMode", "Math|Trig|", "Utilities|FlowControl|",
              "Math|Vector|Distance", "Math|Vector|Normalize", "Math|Vector|Lerp", "Math|Float|Lerp", "Math|Vector|LerpVector",
              "SetAnim", "ReturnToIdle", "FleeFrom", "StartApproach", "Math|Float|Max", "Math|Float|Min", "EaseInOut", "Math|Float|Ease"]:
        print(f"## {q}:", BT.find_node_types(g, q)[:25])
    for t in ["Components|Animation|PlayAnimation", "Transformation|SetActorLocationAndRotation",
              "Math|Interpolation|RInterpTo", "Math|Rotator|FindLookatRotation", "Utilities|Time|SetTimerbyFunctionName",
              "Math|Random|RandomFloatinRange", "Actor|GetAllActorsOfClass"]:
        try:
            ni = BT.get_node_type_pins(g, t)
            print(f"## PINS {t}: in={[ (p.name, p.type_id) for p in ni.input_pins]} out={[(p.name, p.type_id) for p in ni.output_pins]}")
        except Exception as e:
            print(f"## PINS {t}: ERR {e}")
    cg = BT.get_graph(ctrl, "EventGraph")
    for q in ["BP_CrowAgent|", "Crow", "GetCrow", "SetCrow", "CastToBP_CrowAgent", "BP_CrowPerch"]:
        print(f"## [ctrl] {q}:", BT.find_node_types(cg, q)[:30])
    # game instance / gong info
    gi = unreal.load_asset("/Game/CustomStuff/Blueprints/Systems/Core/GI_GameManager")
    print("## GI vars:", [str(v.name) if hasattr(v, "name") else str(v) for v in BT.list_variables(gi)])
    print("## GI funcs:", [str(f.name) for f in BT.list_functions(gi) if f.is_implemented][:60])
    print("## GI events:", [str(e.name) for e in BT.list_events(gi) if e.is_implemented])
    gong = unreal.load_asset("/Game/CustomStuff/Blueprints/Interactables/Main/BP_RealmGong")
    print("## gong vars:", [str(v.name) if hasattr(v, "name") else str(v) for v in BT.list_variables(gong)])
    print("## gong graphs:", [str(x.get_name()) for x in BT.list_graphs(gong)])
    try:
        print("## gong EventGraph DSL:\n" + BT.read_graph_dsl(BT.get_graph(gong, "EventGraph"))[:6000])
    except Exception as e:
        print("gong dsl err", e)
    rs = unreal.load_asset("/Game/CustomStuff/Blueprints/Systems/Core/C_RealmShiftComponent")
    print("## realmshift vars:", [str(v.name) if hasattr(v, "name") else str(v) for v in BT.list_variables(rs)])
    print("## realmshift dispatchers:", BT.list_event_dispatchers(rs))
    print("## GI dispatchers:", BT.list_event_dispatchers(gi))
    for a in EAL.list_assets(FOLDER):
        print("asset", a)
    EAL.save_directory("/Game/Characters/Crow", only_if_is_dirty=True, recursive=True)

run("build_a", main)
