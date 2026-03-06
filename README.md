# 双人访谈分屏视频生成器

使用 Remotion (React) 生成 1080x1080 方形分屏访谈视频，上半部分为 skyhi，下半部分为 ayumu，各自带有头像和字幕，中间分割线处显示注释文字。

## 前提条件

- macOS
- Node.js >= 20
- ffmpeg（用于从 input.mp4 提取音频）

## 目录结构

```
├── src/
│   ├── index.ts          # Remotion 入口
│   ├── Root.tsx           # Composition 注册（1080x1080, 30fps, 30秒）
│   └── Interview.tsx      # 主视频组件（布局、字幕、注释数据）
├── public/
│   ├── skyhi.jpeg         # skyhi 头像
│   ├── ayumu.jpeg         # ayumu 头像
│   └── audio.mp3          # 音频（需从 input.mp4 提取，见下方步骤）
├── package.json
├── package-lock.json
├── tsconfig.json
├── remotion.config.ts
├── input.mp4              # 原始视频（需自行提供）
├── skyhi.jpeg             # 原始头像
├── ayumu.jpeg             # 原始头像
└── sub.json               # 字幕时间轴数据
```

## 在新机器上运行的步骤

### 1. 克隆仓库

```bash
git clone <你的仓库地址>
cd domsub
```

### 2. 准备 input.mp4

`input.mp4` 体积过大，不适合放入 git。需要手动将该文件放到项目根目录下。

### 3. 安装依赖

```bash
npm install
```

### 4. 提取音频

从 `input.mp4` 提取前 30 秒音频到 `public/audio.mp3`：

```bash
ffmpeg -y -i input.mp4 -t 30 -vn -acodec libmp3lame -b:a 192k public/audio.mp3
```

### 5. 渲染视频

```bash
npm run render
```

输出文件为 `output.mp4`（1080x1080, h264, 30fps, 约30秒）。

### 6. 预览（可选）

在浏览器中实时预览：

```bash
npm run studio
```

## 修改字幕/注释

所有字幕和注释数据在 `sub.json` 中维护，修改后重新执行 `npm run render` 即可。

### sub.json 格式

```json
{
  "duration": 30,
  "speakers": {
    "skyhi": [
      { "start": 3.8, "end": 6.8, "text": "我第一次接触音乐是在高中" }
    ],
    "ayumu": [
      { "start": 5.0, "end": 8.0, "text": "所以你是自学的吗" }
    ]
  },
  "annotations": [
    { "start": 0, "end": 5.0, "text": "[音乐]" }
  ]
}
```

- `duration` — 视频总时长（秒），同时决定渲染帧数
- `speakers` — 每个 key 是说话者名字（同时对应 `public/{名字}.jpeg` 头像），第一个在上半部分，第二个在下半部分
- `annotations` — 显示在中间分割线处的注释文字，字号比字幕小一号

### SRT 时间戳格式说明

时间戳从 SRT 格式 `HH:MM:SS,mmm` 换算为秒数：

```
00:00:03,800  →  3.8
00:00:07,610  →  7.61
00:01:30,500  →  90.5
```

### SRT 文件中区分角色

在 SRT 文件中使用 `[名字]` 前缀来标记角色，便于后续转换为 `sub.json`：

```srt
1
00:00:00,000 --> 00:00:05,000
[annotation] [音乐]

2
00:00:03,800 --> 00:00:06,800
[skyhi] 我第一次接触音乐是在高中

3
00:00:05,000 --> 00:00:08,000
[ayumu] 所以你是自学的吗

4
00:00:05,000 --> 00:00:08,000
[annotation] [challenge, creative, path to success]
```

解析时按前缀分流：`[annotation]` 归入 `annotations`，其余归入 `speakers` 对应的 key。
