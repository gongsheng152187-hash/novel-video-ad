import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import textwrap
import numpy as np
import io

# 核心修复：自动兼容云端新旧版 MoviePy
try:
    from moviepy.editor import ImageSequenceClip
except Exception:
    from moviepy import ImageSequenceClip

st.set_page_config(page_title="欧美小说视频生成器-云端专业版", layout="wide")

# --- 自定义绘制函数：支持字间距 ---
def draw_text_with_spacing(draw, text, position, font, fill, char_spacing):
    x, y = position
    for char in text:
        draw.text((x, y), char, font=font, fill=fill)
        char_w = draw.textlength(char, font=font)
        x += char_w + char_spacing

# --- 核心绘制逻辑 ---
def create_frame(text, bg_image, font_path, font_size, text_color, bg_color, opacity, line_spacing, char_spacing):
    img = bg_image.copy().convert("RGBA")
    w, h = img.size
    overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
    draw_ov = ImageDraw.Draw(overlay)

    try:
        font = ImageFont.truetype(font_path, font_size)
    except:
        font = ImageFont.load_default()

    effective_char_w = (font_size * 0.5) + char_spacing
    max_chars_per_line = int((w * 0.85) / effective_char_w)
    wrapped_lines = textwrap.wrap(text, width=max_chars_per_line)
    
    line_h = font_size + line_spacing
    box_h = len(wrapped_lines) * line_h + 60
    box_y = h * 0.6 
    
    bg_rgb = tuple(int(bg_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
    draw_ov.rectangle([40, box_y, w-40, box_y + box_h], fill=(*bg_rgb, opacity))
    img = Image.alpha_composite(img, overlay).convert("RGB")
    
    draw_final = ImageDraw.Draw(img)
    current_y = box_y + 30
    for line in wrapped_lines:
        line_width = sum(draw_final.textlength(c, font=font) for c in line) + (char_spacing * (len(line)-1))
        start_x = (w - line_width) // 2
        draw_text_with_spacing(draw_final, line, (start_x, current_y), font, text_color, char_spacing)
        current_y += line_h
    return img

# --- 升级版分段逻辑：空行为主，句号为辅 ---
def split_text_smartly(full_text, max_chars_per_line):
    # 优先按两个回车（空行）切分大段
    paragraphs = [p.strip() for p in full_text.split('\n\n') if p.strip()]
    final_segments = []
    
    for para in paragraphs:
        # 针对每个大段，如果太长则按句号拆分，确保不爆框（6行上限）
        sentences = [s.strip() + "." for s in para.split('.') if s.strip()]
        current_chunk = ""
        
        for sentence in sentences:
            test_chunk = current_chunk + " " + sentence if current_chunk else sentence
            estimated_lines = len(textwrap.wrap(test_chunk, width=max_chars_per_line))
            
            if estimated_lines > 6 and current_chunk:
                final_segments.append(current_chunk.strip())
                current_chunk = sentence
            else:
                current_chunk = test_chunk
        
        if current_chunk:
            final_segments.append(current_chunk.strip())
    return final_segments

# --- 网页界面 ---
st.title("🎬 欧美小说视频生成器 (云端分享版)")

with st.sidebar:
    st.header("🎨 样式与间距")
    f_size = st.slider("字号", 20, 150, 60)
    line_spacing = st.slider("行间距", 0, 100, 20)
    char_spacing = st.slider("字间距", -5, 20, 0)
    t_color = st.color_picker("字体颜色", "#FFFFFF")
    b_color = st.color_picker("背景颜色", "#000000")
    b_opacity = st.slider("背景透明度", 0, 255, 180)
    st.header("⏱️ 阅读节奏")
    wpm = st.number_input("阅读速度 (WPM)", value=180)

uploaded_img = st.file_uploader("1. 上传背景图", type=["jpg", "png", "jpeg"])
raw_text = st.text_area("2. 粘贴英文文案 (支持空行分段)", height=250)

if st.button("🚀 生成视频并预览"):
    if uploaded_img and raw_text:
        # 使用 BytesIO 确保云端兼容
        image_data = uploaded_img.read()
        bg = Image.open(io.BytesIO(image_data))
        
        effective_char_w = (f_size * 0.5) + char_spacing
        max_chars_per_line = int((bg.size[0] * 0.85) / effective_char_w)
        segments = split_text_smartly(raw_text, max_chars_per_line)
        
        frames = []
        durations = []
        
        with st.status("正在云端合成中...", expanded=True) as status:
            for i, seg in enumerate(segments):
                words = len(seg.split())
                sec = max(2.5, (words / wpm) * 60)
                frame_img = create_frame(seg, bg, "font.ttf", f_size, t_color, b_color, b_opacity, line_spacing, char_spacing)
                frames.append(np.array(frame_img))
                durations.append(sec)
            
            clip = ImageSequenceClip(frames, durations=durations)
            output_file = "cloud_video.mp4"
            clip.write_videofile(output_file, fps=24, codec="libx264", audio=False)
            status.update(label="视频制作完成！", state="complete")
        
        st.video(output_file)
        with open(output_file, "rb") as f:
            st.download_button("💾 下载视频", f, "novel_ad.mp4")
