import os
import glob
import random
from PIL import Image, ImageEnhance
import numpy as np
import cv2

def overlay_images(material_dir, target_dir, output_dir):
    """
    将素材图片叠加到目标图片的非黑色区域，降低非黑色区域的饱和度，并使合成更自然
    """
    # 创建输出目录（如果不存在）
    os.makedirs(output_dir, exist_ok=True)
    
    # 获取所有素材图片
    material_images = glob.glob(os.path.join(material_dir, "*.png"))
    
    # 获取所有目标图片
    target_images = glob.glob(os.path.join(target_dir, "*.png"))
    
    # 对于每个目标图片
    for target_path in target_images:
        target_filename = os.path.basename(target_path)
        
        # 随机选择一个素材图片
        material_path = random.choice(material_images) if material_images else None
        
        # 如果没有任何素材图片，跳过
        if material_path is None:
            print(f"没有找到任何素材图片，跳过 {target_filename}")
            continue
        
        try:
            # 打开目标图片 (RGB)
            target_img = Image.open(target_path).convert("RGB")
            target_array = np.array(target_img)
            
            # 创建掩码：目标图片中非黑色的部分
            black_threshold = 10
            mask = ((target_array[:,:,0] > black_threshold) | 
                    (target_array[:,:,1] > black_threshold) | 
                    (target_array[:,:,2] > black_threshold))
            
            # 找到非黑色区域的边界框
            nonzero_y, nonzero_x = np.where(mask)
            if len(nonzero_y) == 0 or len(nonzero_x) == 0:
                print(f"图片 {target_filename} 没有非黑色区域，跳过")
                continue
                
            min_x, max_x = np.min(nonzero_x), np.max(nonzero_x)
            min_y, max_y = np.min(nonzero_y), np.max(nonzero_y)
            
            # 计算非黑色区域的宽度和高度
            roi_width = max_x - min_x
            roi_height = max_y - min_y
            
            # 打开素材图片 (RGBA)
            material_img = Image.open(material_path).convert("RGBA")
            
            # 创建一个处理后的目标图像副本
            processed_target = target_img.copy()
            
            # 降低非黑色区域的饱和度
            # 先将目标图像转换为OpenCV格式以便处理HSV
            target_cv = cv2.cvtColor(np.array(target_img), cv2.COLOR_RGB2BGR)
            # 转换为HSV颜色空间
            hsv = cv2.cvtColor(target_cv, cv2.COLOR_BGR2HSV)
            # 降低饱和度 (S 通道)30%
            hsv[:,:,1] = np.where(mask, hsv[:,:,1] * 0.99, hsv[:,:,1])  
            # 转回BGR然后再到RGB
            target_cv = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
            processed_target = Image.fromarray(cv2.cvtColor(target_cv, cv2.COLOR_BGR2RGB))
            
            # 根据ROI调整素材大小
            scale_factor = random.uniform(0.05, 0.2)  # 缩小
            target_width = int(roi_width * scale_factor)
            target_height = int(roi_height * scale_factor)
            
            # 保持素材的宽高比
            material_aspect = material_img.width / material_img.height
            roi_aspect = target_width / target_height if target_height > 0 else 1
            
            if material_aspect > roi_aspect:
                # 按宽度缩放
                new_width = target_width
                new_height = int(new_width / material_aspect)
            else:
                # 按高度缩放
                new_height = target_height
                new_width = int(new_height * material_aspect)
                
            # 缩放素材图片
            material_img = material_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # 调整素材的透明度
            material_array = np.array(material_img)
            if material_array.shape[2] == 4:  # 检查是否有alpha通道
                # 降低透明度到70%
                material_array[:,:,3] = (material_array[:,:,3] * 0.95).astype(np.uint8)
                material_img = Image.fromarray(material_array)
            
            # 计算素材放置位置，使其大致居中于ROI
            paste_x = min_x + (roi_width - new_width) // 4
            paste_y = min_y + (roi_height - new_height) // 4
            
            # 将处理后的目标图像转为RGBA
            processed_target_rgba = processed_target.convert("RGBA")
            
            # 创建一个临时图像用于放置素材
            temp_img = Image.new("RGBA", target_img.size, (0, 0, 0, 0))
            temp_img.paste(material_img, (paste_x, paste_y), material_img)
            
            # 使用alpha_composite进行合成
            final_img = Image.alpha_composite(processed_target_rgba, temp_img)

            # 创建与目标图像相同颜色的背景（保持黑色区域的一致性）
            background = Image.new("RGB", final_img.size, (0, 0, 0))

            # 将RGBA图像合成到背景上
            final_img_rgb = Image.alpha_composite(background.convert("RGBA"), final_img).convert("RGB")

            # 保存RGB结果
            output_path = os.path.join(output_dir, target_filename)
            final_img_rgb.save(output_path)
            
            print(f"处理完成: {target_filename}, 使用素材: {os.path.basename(material_path)}")
            print(f"  非黑色区域大小: {roi_width}x{roi_height}, 素材调整大小: {new_width}x{new_height}")
            
        except Exception as e:
            print(f"处理 {target_filename} 时出错: {str(e)}")
    
    print("所有图片处理完成!")

# 主函数
if __name__ == "__main__":
    material_dir = "/data_4T//code/PS/素材"
    target_dir = "/data_4T//code/PS/yolo测试_无标签"
    output_dir = "/data_4T//code/PS/叠加结果_1"
    
    overlay_images(material_dir, target_dir, output_dir)
