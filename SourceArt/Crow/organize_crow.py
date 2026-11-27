"""Tidies the imported crow assets and reports the mesh orientation.
Run in the Unreal console:  py "D:/Git/Yumegatari/SourceArt/Crow/organize_crow.py"
"""
import unreal
EAL = unreal.EditorAssetLibrary
ROOT = "/Game/Characters/Crow"

def log(m): unreal.log("CROW_ORG " + m)

moves = {}
for p in EAL.list_assets(ROOT, recursive=True, include_folder=False):
    obj_path = p.split(".")[0]
    name = obj_path.rsplit("/", 1)[1]
    cls = EAL.find_asset_data(p).asset_class_path.asset_name
    if cls == "AnimSequence":
        short = name.replace("SK_CrowCrow_", "").replace("SK_Crow_Crow_", "").replace("Crow_", "")
        moves[obj_path] = f"{ROOT}/Animations/AS_Crow_{short}"
    elif cls == "SkeletalMesh":
        moves[obj_path] = f"{ROOT}/Mesh/SK_Crow"
    elif cls == "Skeleton":
        moves[obj_path] = f"{ROOT}/Mesh/SKEL_Crow"
    elif cls == "PhysicsAsset":
        moves[obj_path] = f"{ROOT}/Mesh/PHYS_Crow"
    elif cls in ("MaterialInstanceConstant", "Material"):
        moves[obj_path] = f"{ROOT}/Materials/{name.replace('M_', 'MI_', 1)}"
for src, dst in moves.items():
    if src != dst:
        ok = EAL.rename_asset(src, dst)
        log(f"{'moved' if ok else 'FAILED'} {src} -> {dst}")
EAL.save_directory(ROOT, only_if_is_dirty=False, recursive=True)

# remove now-empty folders left by the importer
for f in sorted(EAL.list_assets(ROOT, recursive=True, include_folder=True), key=len, reverse=True):
    if f.endswith("/") and not EAL.list_assets(f, recursive=True, include_folder=False):
        EAL.delete_directory(f)

mesh = unreal.load_asset(f"{ROOT}/Mesh/SK_Crow")
b = mesh.get_bounds()
log(f"bounds origin={b.origin} extent={b.box_extent}")
skel_ctrl = unreal.SkeletalMeshEditorSubsystem if hasattr(unreal, "SkeletalMeshEditorSubsystem") else None
try:
    head = mesh.get_skeleton().get_reference_pose().get_ref_bone_pose("head", unreal.AnimPoseSpaces.WORLD)
    log(f"head bone world location={head.translation}")
except Exception as e:
    log(f"head lookup skipped: {e}")
for p in EAL.list_assets(ROOT, recursive=True, include_folder=False):
    log(f"asset {p}")

fly = unreal.load_asset(f"{ROOT}/Animations/AS_Crow_Fly")
if fly:
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).open_editor_for_assets([fly])
    log("opened AS_Crow_Fly")
