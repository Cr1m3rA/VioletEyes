# VioletEyes 品牌资产（apps/web/public）

## Logo 文件

| 文件 | 来源 | 用途 |
|---|---|---|
| `logo-white.png` | `C:\Users\Jerome\Documents\CCworkspace\VioletEyes.png` | 白底 logo，浅色文档 / README / 邮件签名 |
| `logo-transparent.png` | `C:\Users\Jerome\Documents\CCworkspace\VioletEyes-1.png` | 透明背景 logo，深色 Cover / Header / favicon |
| `favicon.png` | `logo-transparent.png` 的副本 | 浏览器标签图标 |

## Logo 组件用法

```tsx
import { Logo } from '@/components/brand/Logo';

<Logo variant="gradient" size="md" />              // 纯代码渐变方块 + VE（默认）
<Logo variant="image-transparent" size="lg" />     // 透明背景图片 + 文字
<Logo variant="image-white" size="sm" />           // 白底图片
<Logo variant="image-transparent" showText={false} /> // 仅图标
```

## 视觉规则

- **Header (sticky, light bg)**: 使用 `image-transparent`（透明背景在白底上看起来干净）
- **Cover hero (dark gradient bg)**: 使用 `image-transparent`（紫罗兰图标在深色上更突出）
- **LoginPage (dark gradient bg)**: 使用 `image-transparent` 同上
- **README / 文档**: 使用 `image-white`（白底保证可读性）
- **纯代码场景（无图片资源时）**: 使用 `gradient`（与 VioletEyes 报告 base.html.j2 视觉一致）
- **favicon**: 使用 `favicon.png`（自动从 index.html link 加载）

## 修改 logo

替换 `logo-white.png` / `logo-transparent.png` 即可，无需改代码。
注意保持文件名稳定（被 Logo.tsx 引用）。

## 来源

- 原始文件位于：`C:\Users\Jerome\Documents\CCworkspace\`
- 复制命令：`cp /c/Users/Jerome/Documents/CCworkspace/VioletEyes*.png apps/web/public/`