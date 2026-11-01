#!/bin/zsh
cd "/Users/alissachang/大專" || exit 1
"/Applications/Blender.app/Contents/MacOS/Blender" --background --python "/Users/alissachang/大專/blender_make_seam_fillers.py" || exit 1
echo
echo "完成後請查看："
echo "/Users/alissachang/大專/傘面板件接縫填充_五款.blend"
echo "/Users/alissachang/大專/接縫填充_STL/"
echo "/Users/alissachang/大專/傘面板件接縫填充_五款尺寸.csv"
echo "/Users/alissachang/大專/傘面板件接縫填充_五款預覽.png"
echo
echo "按 Enter 關閉視窗"
read
