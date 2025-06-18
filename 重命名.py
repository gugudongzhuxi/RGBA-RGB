import os
import glob

def rename_png_files(directory):
    """
    将指定目录中的所有PNG图片文件名在.png前加上(1)
    例如: image.png -> image(1).png
    
    Args:
        directory: 包含PNG文件的目录路径
    """
    # 获取所有的.png文件
    png_files = glob.glob(os.path.join(directory, "*.png"))
    
    renamed_count = 0
    skipped_count = 0
    
    print(f"在目录 {directory} 中找到 {len(png_files)} 个PNG文件")
    
    # 遍历每个文件并重命名
    for file_path in png_files:
        # 获取文件目录和文件名
        dir_name = os.path.dirname(file_path)
        file_name = os.path.basename(file_path)
        
        # 分离文件名和扩展名
        name, ext = os.path.splitext(file_name)
        
        # 创建新的文件名：原名称 + (1) + 扩展名
        new_name = f"{name}(rand)(1){ext}"
        new_path = os.path.join(dir_name, new_name)
        
        # 检查新文件名是否已存在
        if os.path.exists(new_path):
            print(f"跳过: {file_name} (目标文件 {new_name} 已存在)")
            skipped_count += 1
            continue
        
        try:
            # 重命名文件
            os.rename(file_path, new_path)
            print(f"已重命名: {file_name} -> {new_name}")
            renamed_count += 1
        except Exception as e:
            print(f"重命名 {file_name} 时出错: {str(e)}")
    
    print(f"重命名完成: {renamed_count} 个文件已重命名, {skipped_count} 个文件被跳过")

# 使用示例
if __name__ == "__main__":
    # 替换为您的目录路径
    target_directory = "/data_4T/zy_GCJX_607/code/PS/叠加结果_2"
    
    # 执行重命名操作
    rename_png_files(target_directory)
