"""PIE test helper: py test_pie.py report|far|near|gong  (moves the player and logs crow states)."""
import unreal, sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
cmd = sys.argv[1] if len(sys.argv) > 1 else "report"
saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
out = []
MODES = {0: "Perched", 1: "TakingOff", 2: "Circling", 3: "Approaching", 4: "Landing"}
try:
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    if world is None:
        out.append("no PIE world")
    else:
        crow_cls = unreal.load_asset("/Game/Characters/Crow/Blueprints/BP_CrowAgent").generated_class()
        crows = unreal.GameplayStatics.get_all_actors_of_class(world, crow_cls)
        player = unreal.GameplayStatics.get_player_pawn(world, 0)
        target = crows[0] if crows else None
        if target and player and cmd in ("far", "near"):
            c = target.get_actor_location()
            off = unreal.Vector(1600, 0, 0) if cmd == "far" else unreal.Vector(220, 0, 0)
            dest = c + off + unreal.Vector(0, 0, 120)
            player.set_actor_location(dest, False, True)
            ctrl = player.get_controller()
            look = unreal.MathLibrary.find_look_at_rotation(dest, c)
            if ctrl:
                ctrl.set_control_rotation(unreal.Rotator(0, -10, look.yaw))
            out.append(f"moved player to {dest}")
        if cmd == "gong":
            gi = unreal.GameplayStatics.get_game_instance(world)
            gi.call_method("Toggle Realms") if hasattr(gi, "call_method") else None
            out.append("toggled realm")
        for cr in crows:
            mode = cr.get_editor_property("Mode")
            ctrl = cr.get_controller()
            if ctrl:
                try:
                    out.append(f"   ctrl tick={ctrl.is_actor_tick_enabled()} alertR={ctrl.get_editor_property('AlertRadius')} crowvar={ctrl.get_editor_property('Crow')} lastRealm={ctrl.get_editor_property('LastRealm')}")
                except Exception as e:
                    out.append(f"   ctrl err {e}")
            out.append(f"   isAlert={cr.get_editor_property('IsAlert')} rot={cr.get_actor_rotation()}")
            out.append(f"{cr.get_actor_label() if hasattr(cr,'get_actor_label') else cr.get_name()}: mode={MODES.get(mode, mode)} "
                       f"anim={cr.get_editor_property('AnimState')} loc={cr.get_actor_location()} ctrl={ctrl.get_class().get_name() if ctrl else None}")
        if player:
            out.append(f"player at {player.get_actor_location()}")
except Exception as e:
    import traceback; out.append(traceback.format_exc())
open(os.path.join(saved, f"crow_pie_{cmd}.txt"), "w").write("\n".join(out))
unreal.log("CROW_PIE " + cmd + " | " + " || ".join(out)[:800])
