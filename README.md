# Link-detection

检测文件夹（如静态网站存档、前端项目）中缺失的引用文件。

## 功能

- 扫描 HTML/CSS/JS/模板等文件中的资源引用
- 自动检测缺失的图片、样式、脚本、字体等文件
- 支持多种引用模式：href、src、srcset、poster、data-*、CSS url()、@import、JS import/require 等
- 按缺失文件分组报告，列出所有引用来源
- 支持输出详细日志文件

## 安装

无需安装依赖，Python 3.6+ 即可运行。

```bash
git clone https://github.com/wulitian2-png/Link-detection.git
cd Link-detection

## 用法

# 简单用法
1.双击
2.将文件夹拖入窗口，Enter。

# 基本用法
python check_missing.py 文件夹路径

# 输出日志文件
python check_missing.py 文件夹路径 -o 日志.log

# 检查当前目录
python check_missing.py .

支持的引用模式
类别	支持的属性/语法
HTML	href, src, action, srcset, imagesrcset, poster, data, data-*, background, longdesc, profile, cite, formaction, codebase, archive, xlink:href
CSS	url(), @import
JavaScript	import, import() 动态导入, require()

支持的文件类型
脚本会扫描以下扩展名的文本文件：

HTML/CSS/JS 及其变体 (.html, .css, .js, .ts, .jsx, .vue, .scss 等)

模板引擎 (.pug, .ejs, .hbs, .twig, .liquid, .erb 等)

配置文件 (.json, .yaml, .toml, .env 等)

其他文本文件 (.md, .txt, .svg 等)
