import os
import glob
import random
from PIL import Image, ImageEnhance
import numpy as np
import cv2

def overlay_images(material_dir, target_dir, output_dir):
    """
    将素材图片叠加到目标图片的非黑色区域，降低非黑色区域的饱和度，并使合成更自然
    素材放置位置随机，不一定在中间，并确保与黑色区域重叠的部分也变成黑色
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
            
            # 将掩码转换为图像形式，方便后续操作
            mask_image = Image.fromarray(mask.astype(np.uint8) * 255)
            
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
            # 降低饱和度 (S 通道)5%
            hsv[:,:,1] = np.where(mask, hsv[:,:,1] * 0.95, hsv[:,:,1])  
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
            
            # 计算素材可放置区域的最大坐标值
            max_paste_x = max_x - new_width
            max_paste_y = max_y - new_height
            
            # 如果可放置区域太小，则居中放置
            if max_paste_x <= min_x or max_paste_y <= min_y:
                paste_x = min_x + (roi_width - new_width) // 2
                paste_y = min_y + (roi_height - new_height) // 2
                print(f"  区域过小，使用居中放置")
            else:
                # 随机选择放置位置，确保在非黑色区域内
                paste_x = random.randint(min_x, max_paste_x)
                paste_y = random.randint(min_y, max_paste_y)
                
                # 验证放置位置是否在非黑色区域内
                if paste_x < min_x or paste_x + new_width > max_x or paste_y < min_y or paste_y + new_height > max_y:
                    print(f"  警告：计算的位置超出非黑色区域，改为居中放置")
                    paste_x = min_x + (roi_width - new_width) // 2
                    paste_y = min_y + (roi_height - new_height) // 2
            
            # 将处理后的目标图像转为RGBA
            processed_target_rgba = processed_target.convert("RGBA")
            
            # 创建一个临时图像用于放置素材前的处理
            temp_img = Image.new("RGBA", target_img.size, (0, 0, 0, 0))
            
            # 创建一个黑色区域掩码的裁剪版本，对应素材将要放置的区域
            mask_crop = mask[paste_y:paste_y+new_height, paste_x:paste_x+new_width]
            
            # 如果掩码区域与素材大小不匹配（可能是因为素材部分超出图像边界），则进行调整
            if mask_crop.shape[0] != new_height or mask_crop.shape[1] != new_width:
                print(f"  警告：掩码区域大小与素材不匹配，进行调整")
                # 创建一个新的掩码，默认全为黑色区域
                adjusted_mask = np.zeros((new_height, new_width), dtype=bool)
                
                # 计算有效的重叠区域
                overlap_height = min(mask_crop.shape[0], new_height)
                overlap_width = min(mask_crop.shape[1], new_width)
                
                # 将有效区域的掩码复制过来
                adjusted_mask[:overlap_height, :overlap_width] = mask_crop[:overlap_height, :overlap_width]
                mask_crop = adjusted_mask
            
            # 将numpy掩码数组转换为PIL图像格式
            mask_crop_img = Image.fromarray(mask_crop.astype(np.uint8) * 255)
            mask_crop_img = mask_crop_img.resize((new_width, new_height), Image.Resampling.NEAREST)
            
            # 调整素材，使其与黑色区域重叠的部分变为透明
            material_array = np.array(material_img)
            
            # 将掩码也转换为numpy数组以便处理
            mask_crop_array = np.array(mask_crop_img)
            
            # 确保掩码和素材形状匹配
            if mask_crop_array.shape[:2] != material_array.shape[:2]:
                print(f"  警告：掩码和素材形状不匹配，进行调整")
                # 创建适合大小的掩码
                adjusted_mask = np.zeros((material_array.shape[0], material_array.shape[1]), dtype=np.uint8)
                
                # 计算有效的重叠区域
                h = min(mask_crop_array.shape[0], material_array.shape[0])
                w = min(mask_crop_array.shape[1], material_array.shape[1])
                
                # 复制有效区域
                adjusted_mask[:h, :w] = mask_crop_array[:h, :w]
                mask_crop_array = adjusted_mask
            
            # 对于素材中的每个像素，检查它是否会落在目标图片的黑色区域内
            # 如果是，则将其alpha值设为0（完全透明）
            for y in range(material_array.shape[0]):
                for x in range(material_array.shape[1]):
                    # 如果掩码为0（黑色区域），则将素材对应位置的alpha设为0
                    if mask_crop_array[y, x] == 0 and material_array.shape[2] == 4:
                        material_array[y, x, 3] = 0
            
            # 将处理后的素材转回PIL图像
            adjusted_material = Image.fromarray(material_array)
            
            # 粘贴处理后的素材到临时图像
            temp_img.paste(adjusted_material, (paste_x, paste_y), adjusted_material)
            
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
            print(f"  素材放置位置: ({paste_x}, {paste_y})")
            
        except Exception as e:
            print(f"处理 {target_filename} 时出错: {str(e)}")
            import traceback
            traceback.print_exc()
    
    print("所有图片处理完成!")

# 主函数
if __name__ == "__main__":
    material_dir = "/data_4T/zy_GCJX_607/code/PS/素材"
    target_dir = "/data_4T/zy_GCJX_607/code/PS/yolo测试_无标签"
    output_dir = "/data_4T/zy_GCJX_607/code/PS/叠加结果_2"
    
    overlay_images(material_dir, target_dir, output_dir)