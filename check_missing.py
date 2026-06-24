import re
import sys
from pathlib import Path
from urllib.parse import unquote
from collections import defaultdict
# 扩展名
TEXT_EXTENSIONS = {
    '.html', '.htm', '.css', '.js', '.json', '.xml', '.svg',
    '.txt', '.md', '.csv', '.tsv', '.yaml', '.yml', '.ini',
    '.cfg', '.conf', '.log', '.php', '.asp', '.jsp', '.py',
    '.rb', '.pl', '.sh', '.bat', '.cmd', '.ps1',
    '.ts', '.tsx', '.jsx', '.vue', '.svelte', '.mjs', '.cjs',
    '.scss', '.sass', '.less', '.styl',
    '.toml', '.env', '.gitignore', '.editorconfig',
    '.pug', '.jade', '.ejs', '.hbs', '.handlebars',
    '.njk', '.twig', '.liquid', '.mustache', '.erb', '.slim',
    '.xhtml', '.shtml', '.mhtml', '.hta',
    '.pcss', '.stylus', '.sss',
    '.rst', '.coffee', '.ls',
}
# 资源扩展名
ALL_EXTENSIONS = TEXT_EXTENSIONS | {
    '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz',
    '.mp3', '.wav', '.ogg', '.flac', '.aac', '.mid', '.midi',
    '.mp4', '.webm', '.avi', '.flv', '.ogv', '.mov', '.wmv',
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.ico', '.webp', '.tiff',
    '.woff', '.woff2', '.ttf', '.otf', '.eot',
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
    '.swf', '.fla'
}
def is_text_file(filepath: Path) -> bool:
    return filepath.suffix.lower() in TEXT_EXTENSIONS
def find_referenced_files(content: str, base_dir: Path, current_file: Path) -> list:
    """提取文件内容中引用的所有本地文件路径（修复 data-* 属性匹配）"""
    references = []
    urls = set()
    # ---------- 标准核心属性 ----------
    urls.update(re.findall(r'(?:href|src|action)=["\']([^"\']+)["\']', content, re.IGNORECASE))

    # ---------- data-* 自定义属性（修复后支持连字符、数字）----------
    urls.update(re.findall(r'data-[\w-]+=["\']([^"\']+)["\']', content, re.IGNORECASE))

    # ---------- 单独的 data 属性 ----------
    urls.update(re.findall(r'\bdata\s*=\s*["\']([^"\']+)["\']', content, re.IGNORECASE))

    # ---------- poster ----------
    urls.update(re.findall(r'\bposter\s*=\s*["\']([^"\']+)["\']', content, re.IGNORECASE))

    # ---------- xlink:href ----------
    urls.update(re.findall(r'xlink:href\s*=\s*["\']([^"\']+)["\']', content, re.IGNORECASE))

    # ---------- CSS url() ----------
    urls.update(re.findall(r'url\(["\']?([^)"\'\s]+)["\']?\)', content, re.IGNORECASE))

    # ---------- CSS @import ----------
    urls.update(re.findall(r'@import\s+["\']([^"\']+)["\']', content, re.IGNORECASE))

    # ---------- JS 模块 ----------
    urls.update(re.findall(r'''import\s+['"]([^'"]+)['"]''', content))
    urls.update(re.findall(r'''import\s+(?:type\s+)?[\s\w*,{}\n]+?from\s+['"]([^'"]+)['"]''', content))
    urls.update(re.findall(r'''import\s+\*\s+as\s+\w+\s+from\s+['"]([^'"]+)['"]''', content))
    urls.update(re.findall(r'''require\s*\(\s*['"]([^'"]+)['"]\s*\)''', content))
    urls.update(re.findall(r'''import\s*\(\s*['"]([^'"]+)['"]\s*\)''', content))

    # ---------- 其他属性 ----------
    urls.update(re.findall(r'\bbackground\s*=\s*["\']([^"\']+)["\']', content, re.IGNORECASE))

    for m in re.finditer(r'\bimagesrcset\s*=\s*["\']([^"\']+)["\']', content, re.IGNORECASE):
        candidates = m.group(1).split(',')
        for candidate in candidates:
            url_part = candidate.strip().split()[0] if candidate.strip() else ''
            if url_part:
                urls.add(url_part)

    urls.update(re.findall(r'\blongdesc\s*=\s*["\']([^"\']+)["\']', content, re.IGNORECASE))
    urls.update(re.findall(r'\bprofile\s*=\s*["\']([^"\']+)["\']', content, re.IGNORECASE))
    urls.update(re.findall(r'\bcite\s*=\s*["\']([^"\']+)["\']', content, re.IGNORECASE))
    urls.update(re.findall(r'\bformaction\s*=\s*["\']([^"\']+)["\']', content, re.IGNORECASE))
    urls.update(re.findall(r'\bcodebase\s*=\s*["\']([^"\']+)["\']', content, re.IGNORECASE))

    for m in re.finditer(r'\barchive\s*=\s*["\']([^"\']+)["\']', content, re.IGNORECASE):
        for jar in m.group(1).split(','):
            jar = jar.strip()
            if jar:
                urls.add(jar)

    for m in re.finditer(r'srcset\s*=\s*["\']([^"\']+)["\']', content, re.IGNORECASE):
        candidates = m.group(1).split(',')
        for candidate in candidates:
            url_part = candidate.strip().split()[0] if candidate.strip() else ''
            if url_part:
                urls.add(url_part)

    # ---------- 路径解析 ----------
    for url in urls:
        url = url.strip()
        if url.startswith(('http://', 'https://', '//', 'mailto:', 'tel:', 'javascript:', 'data:')):
            continue
        if url.startswith('#'):
            continue
        if not url:
            continue

        url = url.split('?')[0].split('#')[0]
        try:
            url = unquote(url)
        except Exception:
            continue

        if url.startswith('/'):
            target_path = (base_dir / url.lstrip('/')).resolve()
        else:
            target_path = (current_file.parent / url).resolve()

        try:
            target_path.relative_to(base_dir)
        except ValueError:
            continue

        references.append({
            'url': url,
            'path': target_path,
            'from': current_file
        })

    return references

def check_missing_files(archive_dir: str, output_log: str = None):
    """检查缺失文件"""
    base_dir = Path(archive_dir).resolve()

    if not base_dir.exists():
        print(f"[ERROR] 目录不存在: {base_dir}")
        return
    if not base_dir.is_dir():
        print(f"[ERROR] 路径不是目录: {base_dir}")
        return

    print(f"[INFO] 扫描目录: {base_dir}\n")

    # 1. 收集所有已存在的文件
    all_files = set()
    for f in base_dir.rglob("*"):
        if f.is_file():
            all_files.add(f.resolve())
    print(f"[INFO] 目录中共有 {len(all_files)} 个文件")

    # 2. 扫描文本文件，提取所有引用
    all_references = []
    scanned_files = 0
    print("[INFO] 开始扫描文本文件...")
    for f in base_dir.rglob("*"):
        if not f.is_file() or not is_text_file(f):
            continue
        try:
            content = f.read_text(encoding='utf-8', errors='ignore')
        except Exception as e:
            print(f"[WARN] 无法读取: {f.relative_to(base_dir)} - {e}")
            continue

        refs = find_referenced_files(content, base_dir, f)
        all_references.extend(refs)
        scanned_files += 1
        if scanned_files % 50 == 0:
            print(f"[PROGRESS] 已扫描 {scanned_files} 个文本文件...")

    print(f"[INFO] 共扫描 {scanned_files} 个文本文件")
    print(f"[INFO] 共找到 {len(all_references)} 个引用")

    # 3. 按目标路径聚合引用（保留所有来源文件）
    refs_by_target = defaultdict(list)
    for ref in all_references:
        refs_by_target[ref['path']].append(ref)

    # 4. 检查缺失
    missing = []
    for target_path, refs in refs_by_target.items():
        if target_path in all_files:
            continue  # 文件存在

        # 如果目标是一个真实存在的目录，则视为有效引用
        if target_path.exists() and target_path.is_dir():
            continue

        missing.append({'path': target_path, 'refs': refs})

    # 5. 输出报告
    print()
    print("=" * 60)
    print("缺失文件报告")
    print("=" * 60)
    print(f"总计缺失: {len(missing)} 个文件\n")

    if not missing:
        print("[OK] 没有发现缺失文件！")
        if output_log:
            log_path = Path(output_log)
            log_path.write_text(
                "缺失文件报告\n" + "=" * 60 + "\n" +
                f"扫描目录: {base_dir}\n" +
                "没有发现缺失文件！\n",
                encoding='utf-8'
            )
            print(f"[INFO] 日志已保存到: {log_path.absolute()}")
        return

    # ---- 控制台输出 ----
    for entry in missing:
        try:
            rel_path = entry['path'].relative_to(base_dir)
        except ValueError:
            rel_path = entry['path']
        print(f"[缺失] {rel_path}")
        print(f"  被以下文件引用 ({len(entry['refs'])} 处):")
        for ref in entry['refs']:
            try:
                src = ref['from'].relative_to(base_dir)
            except ValueError:
                src = ref['from']
            print(f"    - {src}  (引用: {ref['url']})")
        print()

    # 类型统计
    ext_count = defaultdict(int)
    for entry in missing:
        ext = entry['path'].suffix.lower() or '(无扩展名)'
        ext_count[ext] += 1

    print("=" * 60)
    print("缺失文件类型统计:")
    for ext, count in sorted(ext_count.items(), key=lambda x: -x[1]):
        print(f"  {ext}: {count} 个")

    # 6. 保存日志
    if output_log:
        log_path = Path(output_log)
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write("缺失文件报告\n")
            f.write("=" * 60 + "\n")
            f.write(f"扫描目录: {base_dir}\n")
            f.write(f"总计缺失: {len(missing)} 个文件\n\n")
            for entry in missing:
                rel_path = entry['path'].relative_to(base_dir) if entry['path'].is_relative_to(base_dir) else entry['path']
                f.write(f"[缺失] {rel_path}\n")
                f.write(f"  被以下文件引用 ({len(entry['refs'])} 处):\n")
                for ref in entry['refs']:
                    src = ref['from'].relative_to(base_dir) if ref['from'].is_relative_to(base_dir) else ref['from']
                    f.write(f"    - {src}  (引用: {ref['url']})\n")
                f.write("\n")
            f.write(f"\n{'='*60}\n")
            f.write("缺失文件类型统计:\n")
            for ext, count in sorted(ext_count.items(), key=lambda x: -x[1]):
                f.write(f"  {ext}: {count} 个\n")
        print(f"\n[INFO] 日志已保存到: {log_path.absolute()}")

    print("\n[完成] 检查完成")

def main():
    if len(sys.argv) > 1:
        import argparse
        parser = argparse.ArgumentParser(description="检测文件夹中缺失的引用文件（增强修复版）")
        parser.add_argument("dir", nargs='?', help="要检测的文件夹路径")
        parser.add_argument("-o", "--output", default=None, help="输出日志文件路径")
        args = parser.parse_args()

        folder_path = args.dir
        output_log = args.output

        if not folder_path:
            folder_path = input("请输入要检测的文件夹路径: ").strip()
            if not folder_path:
                print("[ERROR] 未指定文件夹路径")
                sys.exit(1)
    else:
        print("=" * 60)
        print("缺失文件检测工具")
        print("=" * 60 + "\n")
        folder_path = input("请输入要检测的文件夹路径: ").strip()
        if not folder_path:
            print("[ERROR] 未指定文件夹路径")
            sys.exit(1)
        save_log = input("是否保存日志文件？(y/n, 默认: n): ").strip().lower()
        output_log = "missing_files.log" if save_log == 'y' else None
        if save_log == 'y':
            custom = input("请输入日志文件路径 (默认: missing_files.log): ").strip()
            if custom:
                output_log = custom

    folder_path = folder_path.strip('"\'')
    check_missing_files(folder_path, output_log)
    print()
    input("按回车键退出...")

if __name__ == "__main__":
    main()