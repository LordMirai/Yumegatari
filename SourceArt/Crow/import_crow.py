"""Imports SK_Crow.glb (mesh, skeleton, 6 animations) into /Game/Characters/Crow.
Run in the Unreal console:  py "D:/Git/Yumegatari/SourceArt/Crow/import_crow.py"
"""
import unreal

SRC = r"D:/Git/Yumegatari/SourceArt/Crow/SK_Crow.glb"
DEST = "/Game/Characters/Crow"

task = unreal.AssetImportTask()
task.filename = SRC
task.destination_path = DEST
task.automated = True
task.save = True
task.replace_existing = True
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])

unreal.log("CROW_IMPORT imported objects: %d" % len(task.imported_object_paths))
for p in unreal.EditorAssetLibrary.list_assets(DEST, recursive=True):
    data = unreal.EditorAssetLibrary.find_asset_data(p)
    unreal.log("CROW_IMPORT %s  [%s]" % (p, data.asset_class_path.asset_name))
