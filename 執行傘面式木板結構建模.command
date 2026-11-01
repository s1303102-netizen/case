#!/bin/zsh
cd "/Users/alissachang/大專" || exit 1
"/Applications/Blender.app/Contents/Resources/5.2/python/bin/python3.13" "/Users/alissachang/大專/make_umbrella_canopy_panel_structure.py" || exit 1
"/Applications/Blender.app/Contents/MacOS/Blender" --python "/Users/alissachang/大專/blender_import_umbrella_canopy_structure.py"
echo
echo "完成後請查看："
echo "/Users/alissachang/大專/內部圓弧傘面木板結構.blend"
echo "/Users/alissachang/大專/內部圓弧傘面木板結構.obj"
echo "/Users/alissachang/大專/內部圓弧傘面板件尺寸.csv"
echo "/Users/alissachang/大專/內部圓弧傘面正視分片圖.svg"
echo
echo "按 Enter 關閉視窗"
read
