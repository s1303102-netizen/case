#!/bin/zsh
cd "/Users/alissachang/大專" || exit 1
"/Applications/Blender.app/Contents/MacOS/Blender" --python "/Users/alissachang/大專/blender_make_wood_curve_structure.py"
echo
echo "完成後請查看："
echo "/Users/alissachang/大專/木板曲面結構_精準分段.blend"
echo "/Users/alissachang/大專/木板曲面板件尺寸.csv"
echo "/Users/alissachang/大專/木板曲面剖面尺寸圖.svg"
echo
echo "按 Enter 關閉視窗"
read
