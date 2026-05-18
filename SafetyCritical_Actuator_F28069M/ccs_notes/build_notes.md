# CCS Build Notes

## Recommended CCS Target Setup

| Setting | Value |
|---|---|
| Target family | 2806x Piccolo |
| Device | TMS320F28069M |
| Debug probe | onboard LaunchPad XDS100v2-compatible debugger |
| Compiler | TI C2000 compiler |

## Required controlSUITE Support Files

Use linked files from:

```text
C:\ti\controlSUITE\device_support\f2806x\v151
```

Required source files:

```text
F2806x_CodeStartBranch.asm
F2806x_SysCtrl.c
F2806x_Gpio.c
F2806x_PieCtrl.c
F2806x_PieVect.c
F2806x_DefaultIsr.c
F2806x_usDelay.asm
F2806x_GlobalVariableDefs.c
```

Required linker command files:

```text
F28069M.cmd
F2806x_Headers_nonBIOS.cmd
```

## Important Linker Rule

Use only one device memory linker command file and one header linker command file.

Do not add every `.cmd` file from the controlSUITE folder. Multiple linker maps will create overlapping memory-range errors.

## Include Paths

```text
C:\ti\controlSUITE\device_support\f2806x\v151\F2806x_common\include
C:\ti\controlSUITE\device_support\f2806x\v151\F2806x_headers\include
```

## Cleaner Utility

If a CCS project gets polluted with extra linked controlSUITE files, use:

```powershell
python tools\clean_ccs_project.py "C:\path\to\SafetyCritical_Actuator_F28069M"
```
