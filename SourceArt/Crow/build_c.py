"""Step C: replace old BP_Crow actors in the open level with BP_CrowAgent and add perches nearby."""
import unreal, sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from crow_run import run

def main():
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    print("level:", world.get_name())
    old_cls = unreal.load_asset("/Game/Characters/Birds/Blueprints/BP_Crow").generated_class()
    new_cls = unreal.load_asset("/Game/Characters/Crow/Blueprints/BP_CrowAgent").generated_class()
    perch_cls = unreal.load_asset("/Game/Characters/Crow/Blueprints/BP_CrowPerch").generated_class()
    actors = eas.get_all_level_actors()
    olds = [a for a in actors if a.get_class() == old_cls]
    existing_new = [a for a in actors if a.get_class() == new_cls]
    print("old crows:", [(a.get_actor_label(), a.get_actor_location()) for a in olds])
    print("existing agents:", len(existing_new))
    if existing_new:
        print("agents already placed; skipping replacement")
        return
    for a in olds:
        loc = a.get_actor_location(); rot = a.get_actor_rotation()
        # old crow mesh origin may sit above ground: trace down to the surface below it
        hit = unreal.SystemLibrary.line_trace_single(world, loc + unreal.Vector(0, 0, 50), loc - unreal.Vector(0, 0, 3000),
                                                     unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [a], unreal.DrawDebugTrace.NONE, True)
        ground = loc
        if hit:
            ground = hit.to_tuple()[4]  # Location
        print("old", a.get_actor_label(), "at", loc, "ground", ground)
        crow = eas.spawn_actor_from_class(new_cls, ground, unreal.Rotator(0, 0, rot.yaw))
        crow.set_actor_label(a.get_actor_label().replace("BP_Crow", "BP_CrowAgent"))
        # perches: three spots around the crow, snapped to whatever surface is below
        for i, ang in enumerate((40, 160, 280)):
            r = 1500.0
            p = ground + unreal.Vector(math.cos(math.radians(ang)) * r, math.sin(math.radians(ang)) * r, 0)
            h = unreal.SystemLibrary.line_trace_single(world, p + unreal.Vector(0, 0, 2500), p - unreal.Vector(0, 0, 2500),
                                                       unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [], unreal.DrawDebugTrace.NONE, True)
            pl = h.to_tuple()[4] if h else p
            pa = eas.spawn_actor_from_class(perch_cls, pl, unreal.Rotator(0, 0, ang + 180))
            pa.set_actor_label(f"BP_CrowPerch_{i+1}")
            print("perch", i + 1, pl, "hit" if h else "no-hit")
        eas.destroy_actor(a)
        print("replaced", crow.get_actor_label())
        sel = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        sel.set_selected_level_actors([crow])

run("build_c", main)
