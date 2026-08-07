from pathlib import Path
import shutil
import sys
import xml.etree.ElementTree as ET

CONTROL_SUITE = Path(r"C:\ti\controlSUITE")
PROJECT_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
F2806X_BASE = CONTROL_SUITE / r"device_support\f2806x\v151"

KEEP_FILES = {
    "main.c",
    "F2806x_CodeStartBranch.asm",
    "F2806x_SysCtrl.c",
    "F2806x_Gpio.c",
    "F2806x_PieCtrl.c",
    "F2806x_PieVect.c",
    "F2806x_DefaultIsr.c",
    "F2806x_usDelay.asm",
    "F2806x_GlobalVariableDefs.c",
    "F28069M.cmd",
    "F2806x_Headers_nonBIOS.cmd",
}

REQUIRED_LINKS = {
    "F2806x_CodeStartBranch.asm": F2806X_BASE / r"F2806x_common\source\F2806x_CodeStartBranch.asm",
    "F2806x_SysCtrl.c": F2806X_BASE / r"F2806x_common\source\F2806x_SysCtrl.c",
    "F2806x_Gpio.c": F2806X_BASE / r"F2806x_common\source\F2806x_Gpio.c",
    "F2806x_PieCtrl.c": F2806X_BASE / r"F2806x_common\source\F2806x_PieCtrl.c",
    "F2806x_PieVect.c": F2806X_BASE / r"F2806x_common\source\F2806x_PieVect.c",
    "F2806x_DefaultIsr.c": F2806X_BASE / r"F2806x_common\source\F2806x_DefaultIsr.c",
    "F2806x_usDelay.asm": F2806X_BASE / r"F2806x_common\source\F2806x_usDelay.asm",
    "F2806x_GlobalVariableDefs.c": F2806X_BASE / r"F2806x_headers\source\F2806x_GlobalVariableDefs.c",
    "F28069M.cmd": F2806X_BASE / r"F2806x_common\cmd\F28069M.cmd",
    "F2806x_Headers_nonBIOS.cmd": F2806X_BASE / r"F2806x_headers\cmd\F2806x_Headers_nonBIOS.cmd",
}

def backup_file(path: Path):
    backup = path.with_suffix(path.suffix + ".bak")
    shutil.copy2(path, backup)
    print(f"[backup] {path.name} -> {backup.name}")

def clean_project_xml(project_dir: Path):
    project_file = project_dir / ".project"

    if not project_file.exists():
        print("[skip] No .project file found.")
        return

    backup_file(project_file)

    tree = ET.parse(project_file)
    root = tree.getroot()

    linked = root.find("linkedResources")
    if linked is None:
        linked = ET.SubElement(root, "linkedResources")

    for link in list(linked.findall("link")):
        name_node = link.find("name")
        if name_node is None or not name_node.text:
            continue

        name = Path(name_node.text).name

        remove = False
        if name not in KEEP_FILES:
            if name.startswith("F2806x_") and Path(name).suffix.lower() in {".c", ".asm", ".cmd"}:
                remove = True
            elif Path(name).suffix.lower() == ".cmd":
                remove = True

        if remove:
            print(f"[remove linked] {name}")
            linked.remove(link)

    existing_names = {
        Path(link.find("name").text).name
        for link in linked.findall("link")
        if link.find("name") is not None and link.find("name").text
    }

    for name, target in REQUIRED_LINKS.items():
        if not target.exists():
            print(f"[missing source] {target}")
            continue

        if name in existing_names:
            print(f"[keep linked] {name}")
            continue

        link = ET.SubElement(linked, "link")
        ET.SubElement(link, "name").text = name
        ET.SubElement(link, "type").text = "1"
        ET.SubElement(link, "location").text = str(target)
        print(f"[add linked] {name}")

    tree.write(project_file, encoding="UTF-8", xml_declaration=True)
    print("[write] Updated .project")

def main():
    print(f"[project] {PROJECT_DIR}")

    if not PROJECT_DIR.exists():
        raise SystemExit(f"Project folder does not exist: {PROJECT_DIR}")

    clean_project_xml(PROJECT_DIR)

    print("\nDone.")
    print("Now reopen/refresh the project in CCS, then build again.")
    print("Keep only these linker files visible in Project Explorer:")
    print("  F28069M.cmd")
    print("  F2806x_Headers_nonBIOS.cmd")

if __name__ == "__main__":
    main()
