import unreal, os, glob, shutil
eng = unreal.Paths.convert_relative_path_to_full(unreal.Paths.engine_plugins_dir())
dst = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()), "ToolsetsSrc")
n = 0
for f in glob.glob(os.path.join(eng, "Experimental", "Toolsets", "*", "Content", "Python", "**", "*.py"), recursive=True):
    if os.sep + "tests" + os.sep in f and "blueprint" not in f and "behavior" not in f:
        continue
    rel = os.path.relpath(f, os.path.join(eng, "Experimental", "Toolsets"))
    out = os.path.join(dst, rel); os.makedirs(os.path.dirname(out), exist_ok=True)
    shutil.copy2(f, out); n += 1
unreal.log(f"CROW_COPY copied {n} files to {dst}")
