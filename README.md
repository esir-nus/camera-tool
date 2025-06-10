# 📷 Camera-Tool - 智能摄像头检测工具

## 🌟 项目简介

Camera-Tool 是一个独立的摄像头检测脚本，配备先进的图形用户界面（GUI）。该工具专为机器人视觉应用设计，支持实时物体检测、人脸识别和机器人导航辅助。

### ✨ 主要特性

- **🎯 实时检测**: 支持阅读材料和人脸的实时检测
- **🤖 机器人导航**: 提供精确的机器人移动指导数据
- **🖥️ 现代GUI**: 基于Tkinter的直观用户界面
- **⚡ 可配置帧率**: 支持0.5s、1.0s、2.0s每帧的灵活配置
- **📜 CLI风格历史**: 专业的命令行风格检测历史记录
- **📊 数据导出**: 支持JSON和CSV格式的数据导出

## 🔧 新功能 (2025年1月)

### 📈 可配置帧率控制
- **高频捕获**: 0.5秒每帧 - 适用于实时应用
- **标准捕获**: 1.0秒每帧 - 默认设置，平衡性能
- **低频捕获**: 2.0秒每帧 - 适用于资源受限设备
- **实时调整**: 无需重启摄像头即可切换帧率

### 🖼️ 增强CLI风格检测历史
- **深色主题**: 类似终端的黑色背景和绿色文字
- **双显示模式**:
  - **详细模式**: 多行详细检测事件，包含表情符号
  - **紧凑模式**: 单行摘要，便于快速浏览
- **高级控制**:
  - 详细/紧凑模式切换
  - 自动滚动开关
  - 清除历史功能
- **增强容量**: 支持100个检测事件（相比之前的50个）

## 🛠️ 安装要求

### Python 依赖
```bash
pip install -r requirements.txt
```

### 核心依赖包
- `opencv-python` - 计算机视觉处理
- `ultralytics` - YOLO目标检测
- `PIL/Pillow` - 图像处理
- `tkinter` - GUI界面（Python标准库）
- `numpy` - 数值计算

## 🚀 快速开始

### 1. 克隆项目
```bash
git clone https://github.com/esir-nus/camera-tool.git
cd camera-tool
```

### 2. 安装依赖
```bash
# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 3. 启动GUI
```bash
python camera_gui.py
```

## 📱 使用方法

### 🎮 基础操作

1. **启动摄像头**: 点击"Start Camera"按钮
2. **调整帧率**: 在"Frame Rate"下拉菜单中选择所需间隔
3. **开始会话**: 点击"Start Session"开始保存图像
4. **查看检测**: 实时检测数据将显示在右侧面板
5. **历史记录**: 在CLI风格面板中查看详细检测历史

### ⚙️ 高级功能

#### 帧率控制
- **0.5s每帧**: 适用于需要高响应速度的机器人控制
- **1.0s每帧**: 标准设置，适合大多数应用场景
- **2.0s每帧**: 节省资源，适用于监控类应用

#### CLI历史模式
```bash
# 详细模式示例
[15:45:59.123] === 检测事件 ===
📖 阅读材料: 1个检测到
  ├─ 材料1: 位置=(120,85) 尺寸=(200x150) 置信度=89.0% ✓ 已居中
👤 人脸: 2个检测到
  ├─ 人脸1: 位置=(50,60) 尺寸=(80x80)
  ├─ 人脸2: 位置=(200,120) 尺寸=(75x75)
🤖 机器人: MOVE_RIGHT_DOWN | 移动幅度=128.0px | 向量=(100,80)
============================================================

# 紧凑模式示例
[15:45:59.123] M:1 F:2 R:MOVE_RIGHT_DOWN(128px)
```

## 🎛️ GUI界面说明

### 控制面板
- **会话控制**: 开始/结束图像保存会话
- **摄像头控制**: 启动/停止摄像头
- **帧率控制**: 实时调整捕获间隔
- **数据控制**: 获取当前帧、自动更新、设置

### 检测数据显示
- **📖 阅读材料**: 显示检测到的阅读材料详情
- **👤 人脸检测**: 显示人脸数量和位置信息
- **🤖 机器人导航**: 显示移动方向和幅度建议
- **📊 会话信息**: 显示会话状态和性能指标

### CLI风格历史记录
- **详细模式**: 完整的检测信息，包含置信度、位置、机器人指令
- **紧凑模式**: 简洁的单行摘要
- **自动滚动**: 可选择是否自动滚动到最新事件
- **历史导航**: 支持垂直和水平滚动浏览

## 🤖 机器人集成

### 移动幅度说明
移动幅度 = 机器人居中物体所需的总像素距离：
- **0像素**: 完美居中（无需移动）
- **1-30像素**: 精细调整
- **31-100像素**: 中等移动
- **101-200像素**: 大幅调整
- **200+像素**: 主要重新定位

### 数据输出格式
```json
{
  "reading_materials": [
    {
      "box": [120, 85, 200, 150],
      "confidence": 0.89,
      "bbox_center_x": 220,
      "bbox_center_y": 160,
      "is_centered": false
    }
  ],
  "faces": [
    {"box": [50, 60, 80, 80], "face_id": 1}
  ],
  "robot_guidance": {
    "arrow_dx": 100,
    "arrow_dy": 80,
    "movement_magnitude": 128.0,
    "robot_command": "MOVE_RIGHT_DOWN"
  }
}
```

## 📁 项目结构

```
camera-tool/
├── camera_gui.py              # 主GUI应用程序
├── camera-tool.py             # 命令行版本
├── tools/
│   └── camera_tool.py         # 核心检测工具
├── utils/
│   ├── settings.py            # 配置管理
│   └── logging_config.py      # 日志配置
├── models/                    # 检测模型文件
├── requirements.txt           # Python依赖
└── README.md                  # 项目说明（本文件）
```

## 🧪 测试

### 功能测试
```bash
# 运行新功能测试套件
python test_new_features.py

# 测试输出示例：
# 🔍 测试帧率控制功能...
# ✓ 帧率 '0.5s per image' 映射到 500ms
# ✓ 帧率 '1.0s per image' 映射到 1000ms
# ✓ 帧率 '2.0s per image' 映射到 2000ms
# ✅ 帧率控制测试完成
```

### 基础功能验证
```bash
# 语法检查
python -m py_compile camera_gui.py

# GUI组件测试
python test_gui.py
```

## 🔧 配置选项

### 摄像头设置
- **设备索引**: 选择摄像头设备（默认为0）
- **分辨率**: 设置捕获分辨率
- **检测开关**: 启用/禁用人脸或阅读材料检测

### 性能设置
- **置信度阈值**: 调整检测灵敏度
- **帧率间隔**: 0.5-5.0秒可调
- **GUI更新频率**: 1.0-10.0秒可调

## 📤 数据导出

支持多种格式的数据导出：

### JSON格式
```json
{
  "timestamp": 1686407422.547,
  "data_type": "materials",
  "detection_data": {...},
  "session_active": false,
  "camera_running": true
}
```

### CSV格式
```csv
Material_ID,Confidence,X,Y,Width,Height,Centered
1,0.89,120,85,200,150,false
```

## 🛟 故障排除

### 常见问题

1. **ModuleNotFoundError: cv2**
   ```bash
   pip install opencv-python
   ```

2. **摄像头无法启动**
   - 检查摄像头设备索引设置
   - 确认摄像头未被其他应用占用

3. **检测模型加载失败**
   - 确认models/目录下有必需的模型文件
   - 检查模型文件完整性

### 性能优化

- **低配置设备**: 使用2.0s帧率间隔
- **实时应用**: 使用0.5s帧率间隔
- **电池设备**: 关闭自动更新，手动获取帧

## 🤝 贡献指南

1. Fork 本项目
2. 创建功能分支 (`git checkout -b feature/新功能`)
3. 提交更改 (`git commit -am '添加新功能'`)
4. 推送到分支 (`git push origin feature/新功能`)
5. 创建 Pull Request

## 📄 许可证

本项目基于 MIT 许可证开源 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🔗 相关链接

- **GitHub仓库**: https://github.com/esir-nus/camera-tool
- **问题报告**: https://github.com/esir-nus/camera-tool/issues
- **技术文档**: 查看项目中的各种.md文件

## 📞 联系方式

如有问题或建议，请通过GitHub Issues与我们联系。

---

**开发时间**: 2025年1月  
**状态**: ✅ 已完成并测试  
**版本**: v1.0 with Enhanced Features 