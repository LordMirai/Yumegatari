import unreal, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from crow_run import run

def main():
    EAL = unreal.EditorAssetLibrary
    if EAL.does_directory_exist("/Game/Characters/Crow/_Scratch"):
        print("delete scratch:", EAL.delete_directory("/Game/Characters/Crow/_Scratch"))
    ok = unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    print("saved dirty packages:", ok)
    for a in EAL.list_assets("/Game/Characters/Crow", recursive=True):
        print(" ", a)

run("finish", main)
