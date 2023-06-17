define_design_lib WORK -path ./WORK

set TOP_MODULE QID
set src_path "/home/qusdlfrnjs/CryoQC/XQsim_release/src/XQ-estimator/QID/baseline/rtl"
set out_path "/home/qusdlfrnjs/CryoQC/XQsim_release/src/XQ-estimator/QID/baseline/cmos/D5_Q15"
set PDK_path "./freepdk-45nm/stdview"
set SYN_path "/home/synopsys/dc_compiler_2019/syn/P-2019.03/libraries/syn"

set search_path "$src_path \ $PDK_path \ $SYN_path"
set ddc_path "$out_path/${TOP_MODULE}_4k.ddc"

set target_library "$PDK_path/NangateOpenCellLibrary.db"
set synthetic_library "$SYN_path/dw_foundation.sldb"
set link_library "* $target_library $synthetic_library"
set mw_reference_library "./milky-45nm-ideal"
set mw_design_library "./mw_design_lib_ideal"
set technology_file "$PDK_path/rtk-tech-ideal.tf"

open_mw_lib $mw_design_library
check_library

read_ddc ${ddc_path}

redirect ${out_path}/${TOP_MODULE}_critical_path_4k_nowire {report_timing -through [get_pins -of_objects {*}] -through [get_pins -of_objects {  UUT5_0*}]}
redirect ${out_path}/${TOP_MODULE}_power_4k_nowire                   {report_power -hierarchy -levels 10}

exit
