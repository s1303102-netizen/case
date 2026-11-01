#!/bin/zsh
cd "/Users/alissachang/大專" || exit 1
"/Applications/Blender.app/Contents/MacOS/Blender" --python "/Users/alissachang/大專/blender_make_umbrella_trough_wood_structure.py"
echo
echo "完成後請查看："
echo "/Users/alissachang/大專/umbrella_trough_wood_structure.blend"
echo "/Users/alissachang/大專/內部圓弧木板板件尺寸.csv"
echo "/Users/alissachang/大專/內部圓弧木板建模完成.txt"
echo
echo "按 Enter 關閉視窗"
read
